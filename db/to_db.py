import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

df = pd.read_csv("ingredient_emissions.csv")

df.to_sql(
    "ingredient_emissions",
    engine,
    schema="open_beauty",
    if_exists="replace",
    index=False
)

df2 = pd.read_csv("co2_metrics.csv")

df2.to_sql(
    "co2_metrics",
    engine,
    schema="open_beauty",
    if_exists="replace",
    index=False
)