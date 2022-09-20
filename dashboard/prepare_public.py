import pandas as pd
from docenten import hash_nr, preprocess

datapath = "/home/marcel/projects_local/Laura/Docentenbeleid/Data/"

df_raw = pd.read_excel(datapath + "Docenten_2020-2022_220908.xlsx")
df = preprocess(df_raw)

df = hash_nr(df, "persnr")

df.to_excel("../data/Docenten_2020-2022_hashed.xlsx")