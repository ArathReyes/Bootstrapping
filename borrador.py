# -*- coding: utf-8 -*-
"""
Created on Thu Mar 24 18:05:27 2022

@authors: 
    Arath Alejandro Reyes López
    Eduardo de Jesús Cuéllar chávez
    Natasha Monserrath Ortiz Castañeda
"""
from pathlib import Path #Para conocer el path actual
from datetime import datetime, timedelta #Para las fechas
from pandas.tseries.offsets import BDay # Días hábiles
import numpy as np
import pandas as pd #Para dataframes
import seaborn as sns # Graficar
from scipy import interpolate #Para interpolación linear y spline

# today = datetime(2022,3,3) # yy/mm/dd
today = datetime.now()
today = datetime(today.year, today.month, today.day)
spot = today + BDay(1)

#today = today.strftime("%d/%m/%Y")
diahabant = True
par_swap = False

# Dentro de la función

act_360 = True
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


n=390 # Número de cupones
# Esta es la lista de los días inhabiles que proporcionamos de manera particular
inhabiles = [datetime(2022,3,19), datetime(2022, 4, 2)]
#path de la carpeta
path=str(Path(__file__).parent.absolute())
#Nombre del archivo
archivo="/data/datos.xlsx"
#Leemos el archivo
tasas = pd.read_excel(path+archivo, engine='openpyxl')
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


# aux = pd.merge(tasas[1:], df[['Tasa', 'Payment Date']], on = 'Tasa', how = 'left')
# X = list(aux['Payment Date'])
# Y = list(aux['Tasa'])

# df['Tasa'] = df['Payment Date'].apply(interpolacion_lineal_cont, args = (X,Y))

# # ------
# # Auxiliar para convertir a número
# aux_0=pd.isnull(df["Tasa"])
# aux_1=(df["Payment Date"][aux_0==False]).apply(lambda x: (x-datetime(today.year, 
#                                                               today.month, 
#                                                               today.day)).days)
# aux_2=(df["Tasa"][aux_0==False]).to_numpy()

# #Qué tipo decidimos
# if lineal== True:
#     metodo="linear"
# else:
#     metodo="spline"

desc_1_dia=np.exp(-tasas["Tasa"][0]*((spot-today).days)/conv)
if par_swap:
    aux = pd.merge(tasas[1:], df[['Tasa', 'Payment Date']], on = 'Tasa', how = 'left')
    X = list(aux['Payment Date'])
    Y = list(aux['Tasa'])

    df['Tasa'] = df['Payment Date'].apply(interpolacion_lineal_cont, args = (X,Y))
    del X,Y,aux
    aux= np.array(np.zeros([len(df['Tasa'])]))
    aux[0]=desc_1_dia*(1+df['Tasa'][0]*df['Tau'][0])**(-1)
    for i in range(1,len(df['Tasa'])):
        aux[i]=(1-df['Tasa'][i]*sum(df['Tau'][:i]*aux[:i]))/(1+df['Tasa'][i]*df['Tau'][i])
    df['Descuentos'] = aux
    del aux
else:
    df["Plazo"]=(df["Payment Date"]).apply(lambda x: (x-datetime(today.year, 
                                                                  today.month, 
                                                                  today.day)).days/conv)
    desc_29_dias = desc_1_dia / (1+(tasas['Tasa'][1]*(df['Payment Date'][0]-df['Start Date'][0]).days /conv))
    X = [-np.log(desc_29_dias)/df['Plazo'][0]]
    Y = [np.exp(-X[0]*df['Plazo'][0])]
    cum = Y[0]*df['Tau'][0]
    Z = [(desc_1_dia - Y[0])/cum]
    aux = tasas[1:]
    aux = aux.reset_index(drop = True)
    from scipy.optimize import fsolve
    for i in range(1,len(aux)):
        f = lambda x: (desc_1_dia - np.exp(-x*df['Plazo'][i]))/(cum + df['Tau'][i]*np.exp(-x*df['Plazo'][i]))-aux['Tasa'][i]
        X.append(fsolve(f,0)[0])
        Y.append(np.exp(-X[i]*df['Plazo'][i]))
        cum += Y[i]*df['Tau'][i]
        Z.append((desc_1_dia-Y[i])/cum)
    tasas['Continua']= [0] + X
    tasas['Descuentos'] = [0] + Y
    del X,Y,Z,cum,aux
    df = pd.merge(df,tasas[['Cupon','Continua','Descuentos']], on = "Cupon", how="left")
    aux = pd.merge(tasas[1:], df[['Continua', 'Payment Date']], on = 'Continua', how = 'left')
    X = list(aux['Payment Date'])
    Y = list(aux['Tasa'])

    df['Continua'] = df['Payment Date'].apply(interpolacion_lineal_cont, args = (X,Y))
    del X,Y,aux
    aux= np.array(np.zeros([len(df['Continua'])]))
    aux[0]=desc_1_dia*(1+df['Continua'][0]*df['Continua'][0])**(-1)
    for i in range(1,len(df['Continua'])):
        aux[i]=(1-df['Continua'][i]*sum(df['Continua'][:i]*aux[:i]))/(1+df['Continua'][i]*df['Continua'][i])
    df['Descuentos'] = aux
    del aux
    
    
    
# if lineal:
#     #Interpolación elegida
#     int_lin=interpolate.interp1d(aux_1,aux_2,kind='linear')
    
#     #fechas faltantes
#     aux_3=(df["Payment Date"][aux_0]).apply(lambda x: (x-datetime(today.year, 
#                                                                   today.month, 
#                                                                   today.day)).days)
#     #llenamos
#     df.loc[df.Tasa.isnull(), 'Tasa'] = int_lin(aux_3)
    
#     del aux_0,aux_1,aux_2,aux_3 #ya no lo necesitamos
    
#     #descuento a 1 día
#     desc_1_dia=np.exp(-tasas["Tasa"][0]*((spot-today).days)/conv)
    
#     def descuentos(df=df,desc_1_dia=desc_1_dia):
#         x=df["Tasa"]
#         tau=df["Tau"]
#         aux=np.array(np.zeros([len(x)]))
#         aux[0]=desc_1_dia*(1+x[0]*tau[0])**(-1)
#         for i in range(1,len(x)):
#             aux[i]=(1-x[i]*sum(tau[:i]*aux[:i]))/(1+x[i]*tau[i])
#         return(aux)
            
#     df["Descuentos"]=descuentos(df,desc_1_dia)
# else:
    # df["Plazo"]=(df["Payment Date"]).apply(lambda x: (x-datetime(today.year, 
    #                                                               today.month, 
    #                                                               today.day)).days/conv)
    