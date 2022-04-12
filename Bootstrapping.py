# -*- coding: utf-8 -*-
"""
Created on Thu Mar 24 18:05:27 2022

@authors: 
    Arath Alejandro Reyes López
    Eduardo de Jesús Cuéllar chávez
    Natasha Monserrath Ortiz Castañeda
"""

#from pathlib import Path #Para conocer el path actual, para futuros cambios
from datetime import datetime, timedelta #Para las fechas
from pandas.tseries.offsets import BDay # Días hábiles
import numpy as np
import pandas as pd #Para dataframes
import seaborn as sns # Graficar
import matplotlib.pyplot as plt

class Bootstrapping:
    
    def __init__(self):
        self.summary = None
        self.df = None
        self.aux = None
        self.desc_1_dia = None
        self.desc_29_dias = None
        self.descuentos = None
        self.convencion = None
        self.interpolacion = None
        
        
    def  compute(self, par_swap =True,  inhabiles = [], act_360 = True, diahabant = True, archivo = "/data/datos.xlsx"):
        today = datetime.now()
        today = datetime(today.year, today.month, today.day)
        spot = today + BDay(1)
        
        if act_360 == True:
            conv = 360
        else:
            conv = 365  
        
        def UltDiaHabil(x,inhabiles, diahabant):
            while x in inhabiles:
                x = x + ((-1)**diahabant)* BDay(1)
            return x
        
        def interpolacion_lineal_cont(x,X,Y):
            n = len(X)
            for i in range(n-1):
                if X[i]<= x <= X[i+1]:
                    a = Y[i+1] - Y[i]
                    b = (X[i+1] - X[i]).days
                    return Y[i] + (x - X[i]).days*(a/b)
            return "No es posible interpolar"
        
        def f(x,*index):
            i = index
            i=i[0]
            df = self.df
            aux = self.aux
            desc_1_dia = self.desc_1_dia
            #Cambio
            df.loc[i,"Continua"]=x
            #interpolación
            X = list(aux['Payment Date'])
            Y = list(aux['Continua'])
            df['Continua'] = df['Payment Date'].apply(interpolacion_lineal_cont, args = (X,Y))
            del X,Y
            #Sacamos los descuentos
            df["Descuentos"]=np.exp(-df["Continua"]*df["Plazo"])
            
            #Tasa par-swap teórica
            df["Par"]=np.zeros(len(df["Tasa"]))
            for i in range(len(df["Tasa"])):
                df.loc[i,"Par"]=(desc_1_dia-df.loc[i,"Descuentos"])/(sum(df.loc[:(i+1),"Descuentos"]*df.loc[:i+1,"Tau"]))
            df["dif"]=(df["Tasa"]-df["Par"])*(10**8)
            self.df=df
            self.aux=aux
            return (df.loc[i,"Tasa"]-df.loc[i,"Par"])*(10**8)
        
        n=390 # Número de cupones
        #path de la carpeta
        #path ='C:\\Users\\Arath Reyes\\Documents\\GitHub\\Bootstrapping\\data\\'
        path="/Users/cesarjuliocuellarruiz/Documents/Python/Seminario Humberto/Bootstrapping"
        #Leemos el archivo
        #tasas = pd.read_excel(path+archivo, engine='openpyxl')
        tasas = pd.read_excel(path + archivo)
        del path, archivo #Ya no las necesitamos
        
        tasas.rename(columns = {'Unnamed: 1':'Tasa'}, inplace = True) #Renombramos
        tasas = tasas[["Tasa"]]
        tasas["Cupon"] = ["1dia", 1,3,6,9,13,26,39,52,65,91,130,195,260,390] 
        
        """
        CALENDARIO
        """
        
        df = pd.DataFrame()
        df["Cupon"] = list(range(1,n+1))
        
        df["Start Date"] = spot + (df["Cupon"]-1)*timedelta(days=28)
        df["Final Date"] = spot + df["Cupon"]*timedelta(days=28)
        df["Payment Date"] = df["Final Date"] # En México funciona así
        df["Fixing Date"]  = df["Start Date"] - BDay(1)
        
        # Correción de días hábiles
        
        df["Fixing Date"] = df["Fixing Date"].apply(UltDiaHabil, args = (inhabiles,diahabant))        
        df = df[["Cupon","Fixing Date", "Start Date", "Final Date", "Payment Date"]]
        
        # Tau
        df["Tau"] = (df["Final Date"] - df["Start Date"]).dt.days/conv
        
        
        # Agregar las tasas
        df = pd.merge(df,tasas, on = "Cupon", how="left")
        
        desc_1_dia=np.exp(-tasas["Tasa"][0]*((spot-today).days)/conv)
        self.desc_1_dia = desc_1_dia
        if par_swap:
            
            #Interpolamos
            self.interpolacion = "Interpolación Lineal en Tasas Par-Swap"
            aux = pd.merge(tasas[1:], df[['Tasa', 'Payment Date']], on = "Tasa", how = 'left')
            X = list(aux['Payment Date'])
            Y = list(aux['Tasa'])
            df['Tasa'] = df['Payment Date'].apply(interpolacion_lineal_cont, args = (X,Y))
            del X,Y,aux
            
            #Sacamos los descuentos
            aux= np.array(np.zeros([len(df['Tasa'])]))
            aux[0]=desc_1_dia*(1+df['Tasa'][0]*df['Tau'][0])**(-1)
            for i in range(1,len(df['Tasa'])):
                aux[i]=(1-df['Tasa'][i]*sum(df['Tau'][:i]*aux[:i]))/(1+df['Tasa'][i]*df['Tau'][i])
            df['Descuentos'] = aux
            del aux
        else:
            
            desc_29_dias = desc_1_dia / (1+(tasas.loc[1,'Tasa']*(df.loc[0,'Payment Date']-df.loc[0,'Start Date']).days /conv))
            
            self.desc_29_dias = desc_29_dias
            #Plazos y tasas continuas
            self.interpolacion = "Interpolación Lineal en Tasas Continua"
            df["Plazo"]=(df["Payment Date"]).apply(lambda x: (x-datetime(today.year, 
                                                                          today.month, 
                                                                          today.day)).days/conv)
            aux = pd.merge(tasas[1:], df[['Payment Date',"Plazo","Cupon"]], on = 'Cupon', how = 'left')
            #Inicializamos tasa continua
            aux["Continua"]=np.nan
            aux.loc[0,"Continua"]=-np.log(desc_29_dias)/aux.loc[0,"Plazo"]
            aux.loc[1:,"Continua"]=np.random.uniform(0.06,0.09,(len(aux["Plazo"])-1))
            cols_to_use= list(aux.columns.difference(df.columns))
            cols_to_use.append("Cupon")
            df = pd.merge(aux[cols_to_use], df, on = 'Cupon', how = 'right')
            del cols_to_use
            X = list(aux['Payment Date'])
            Y = list(aux['Continua'])
            opt_aux=pd.notna(df["Continua"])
            df['Continua'] = df['Payment Date'].apply(interpolacion_lineal_cont, args = (X,Y))
            del X,Y
            #Sacamos los descuentos
            df["Descuentos"]=np.exp(-df["Continua"]*df["Plazo"])
            #Tasa par-swap teórica
            df["Par"]=np.zeros(len(df["Tasa"]))
            for i in range(len(df["Tasa"])):
                df.loc[i,"Par"]=(desc_1_dia-df.loc[i,"Descuentos"])/(sum(df.loc[:i+1,"Descuentos"]*df.loc[:i+1,"Tau"]))
            #Diferencia
            df["dif"]=(df["Tasa"]-df["Par"])*(10**8)
            #Optimización
            self.df = df
            self.aux= aux
            
            from scipy.optimize import fsolve
            for i in range(0,len(df["Cupon"])):
                #Hay tasa para comparar?
                if opt_aux[i]:
                    fsolve(f,0,args=(i))
            # #Tasa continua
            # aux2["Continua"]=-np.log(aux2["Descuento"]/aux2["Plazo"])
            
            # #Tasas continuas
            # df["Continua"]=-np.log(df["Descuentos"]/(df["Plazo"]))
            # X = list(aux['Payment Date'])
            # Y = list(aux['Tasa'])
            # df['Tasa'] = df['Payment Date'].apply(interpolacion_lineal_cont, args = (X,Y))
            # del X,Y
            
            
            
            # #Sacamos los descuentos
            # aux= np.array(np.zeros([len(df['Tasa'])]))
            # aux[0]=desc_1_dia*(1+df['Tasa'][0]*df['Tau'][0])**(-1)
            # for i in range(1,len(df['Tasa'])):
            #     aux[i]=(1-df['Tasa'][i]*sum(df['Tau'][:i]*aux[:i]))/(1+df['Tasa'][i]*df['Tau'][i])
            # df['Descuentos'] = aux
            # del aux
            
            # X = [-np.log(desc_29_dias)/df['Plazo'][0]] # Continuas
            # Y = [np.exp(-X[0]*df['Plazo'][0])] # Descuentos
            # cum = Y[0]*df['Tau'][0]
            # Z = [(desc_1_dia - Y[0])/cum] # Par-Swap Teóricas
            # aux = tasas[1:]
            # aux = aux.reset_index(drop = True)
            # from scipy.optimize import fsolve
            # for i in range(1,len(aux)):
            #     X.append(fsolve(f,0)[0])
            #     Y.append(np.exp(-X[i]*df['Plazo'][i]))
            #     cum += Y[i]*df['Tau'][i]
            #     Z.append((desc_1_dia-Y[i])/cum)
            # tasas['Continua']= [0] + X
            # tasas['Descuentos'] = [0] + Y
            # tasas['Par-Swap'] = [0] + Z
            # del X,Y,Z,cum,aux
            # df = pd.merge(df,tasas[['Cupon','Continua','Descuentos', 'Par-Swap']], on = "Cupon", how="left")
            # aux = pd.merge(tasas[1:], df[['Continua', 'Payment Date']], on = 'Continua', how = 'left')
            # X = list(aux['Payment Date'])
            # Y = list(aux['Tasa'])
        
            # df['Continua'] = df['Payment Date'].apply(interpolacion_lineal_cont, args = (X,Y))
            # del X,Y,aux
            # aux= np.array(np.zeros([len(df['Continua'])]))
            # aux[0]=desc_1_dia*(1+df['Continua'][0]*df['Continua'][0])**(-1)
            # for i in range(1,len(df['Continua'])):
            #     aux[i]=(1-df['Continua'][i]*sum(df['Continua'][:i]*aux[:i]))/(1+df['Continua'][i]*df['Continua'][i])
            # df['Descuentos'] = aux
            # del aux

        self.summary = df
        self.descuentos = self.summary['Descuentos']
        self.convencion = "Actual / " +str(conv)
            
        return
    
    def plots(self):
        Bool = True
        while Bool:
            print("\n")
            choice = input("Si deseas ver los descuentos teclea 'descuentos', si deseas\
                                ver las tasas teclea 'tasas' o si deseas salir escribe '0':\n")
            if choice == 'descuentos' or choice =='tasas' or choice == '0':
                Bool = False
            else:
                print('\nTu elección no es válida')
        if choice == 'descuentos':
            sns.set_style('darkgrid')
            sns.set_palette('tab10')
            plt.figure(figsize = (12,8))
            ax = sns.lineplot(x = self.summary['Payment Date'], y = self.summary['Descuentos'])
            ax.set_title("Descuentos por "+self.interpolacion,fontsize = '25')
            plt.show()
        elif choice == 'tasas' and self.interpolacion == "Interpolación Lineal en Tasas Par-Swap":
            sns.set_style('darkgrid')
            sns.set_palette('tab10')
            plt.figure(figsize = (12,8))
            ax = sns.lineplot(x = self.summary['Payment Date'], y = self.summary['Tasa'], color = 'red')
            ax.set_title("Tasas por "+self.interpolacion,fontsize = '25')
            plt.show()
        elif choice == 'tasas' and self.interpolacion == "Interpolación Lineal en Tasas Continua":
            sns.set_style('darkgrid')
            sns.set_palette('tab10')
            plt.figure(figsize = (12,8))
            ax = sns.lineplot(x = self.summary['Payment Date'], y = self.summary['Continua'], color = 'red')
            ax.set_title("Tasas por "+self.interpolacion,fontsize = '25')
            plt.show()
        return
