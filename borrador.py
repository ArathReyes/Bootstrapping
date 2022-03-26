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
from scipy import interpolate #Para interpolación linear y spline

# today = datetime(2022,3,3) # yy/mm/dd
today = datetime.now()
today = datetime(today.year, today.month, today.day)
spot = today + BDay(1)

#today = today.strftime("%d/%m/%Y")
diahabant = True
lineal= True
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

# aux = IRS["Fixing Date"]
# aux=[UltDiaHabil(i,inhabiles,diahabant) for i in aux]
# IRS["Fixing Date"] = aux
# del aux

df = df[["Cupon","Fixing Date", "Start Date", "Final Date", "Payment Date"]]

# Tau
df["Tau"] = (df["Final Date"] - df["Start Date"]).dt.days/conv


# Agregar las tasas

df = pd.merge(df,tasas, on = "Cupon", how="left")

#Auxiliar para convertir a número
aux_0=pd.isnull(df["Tasa"])
aux_1=(df["Payment Date"][aux_0==False]).apply(lambda x: (x-datetime(today.year, 
                                                             today.month, 
                                                             today.day)).days)
aux_2=(df["Tasa"][aux_0==False]).to_numpy()

#Qué tipo decidimos
if lineal== True:
    metodo="linear"
else:
    metodo="spline"

if lineal:
    #Interpolación elegida
    int_lin=interpolate.interp1d(aux_1,aux_2,kind=metodo)
    
    #fechas faltantes
    aux_3=(df["Payment Date"][aux_0]).apply(lambda x: (x-datetime(today.year, 
                                                                 today.month, 
                                                                 today.day)).days)
    #llenamos
    df.loc[df.Tasa.isnull(), 'Tasa'] = int_lin(aux_3)
    
    del aux_0,aux_1,aux_2,aux_3 #ya no lo necesitamos
    
    #descuento a 1 día
    desc_1_dia=np.exp(-tasas["Tasa"][0]*((spot-today).days)/conv)
    
    def descuentos(df=df,desc_1_dia=desc_1_dia):
        x=df["Tasa"]
        tau=df["Tau"]
        aux=np.array(np.zeros([len(x)]))
        aux[0]=desc_1_dia*(1+x[0]*tau[0])**(-1)
        for i in range(1,len(x)):
            aux[i]=(1-x[i]*sum(tau[:i]*aux[:i]))/(1+x[i]*tau[i])
        return(aux)
            
    df["Descuentos"]=descuentos(df,desc_1_dia)
else:
    