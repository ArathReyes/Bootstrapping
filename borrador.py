# -*- coding: utf-8 -*-
"""
Created on Thu Mar 24 18:05:27 2022

@author: Arath Alejandro Reyes López
Lolo
Natasha
"""

from datetime import datetime, timedelta
from pandas.tseries.offsets import BDay # Días hábiles
import pandas as pd

# today = datetime(2022,3,3) # yy/mm/dd
today = datetime.now()
today = datetime(today.year, today.month, today.day)
spot = today + timedelta(days = 1)

#today = today.strftime("%d/%m/%Y")
diahabant = True

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


n=390 # Number of coupons
# Esta es la lista de los días inhabiles que proporcionamos de manera particular
inhabiles = [datetime(2022,3,25), datetime(2022, 4, 22)]
tasas = pd.read_excel("C:\\Users\\Arath Reyes\\Desktop\\Python\\Quantitative Finance\\data\\datos.xlsx")
tasas.rename(columns = {'Unnamed: 1':'Tasa'}, inplace = True)
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
