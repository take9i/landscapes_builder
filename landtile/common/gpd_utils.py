# geopandas utilities
import os
import json
import psycopg2
import geopandas as gpd

def get_enveloped_df(db, table, bounds, epsg=4612):
    conn = psycopg2.connect(database=db, user='')
    w, s, e, n = bounds
    sql = "select * from %s where st_within(st_centroid(geom), st_makeenvelope(%f, %f, %f, %f, %d));" % \
        (table, w, s, e, n, epsg);
    return gpd.GeoDataFrame.from_postgis(sql, conn)

def output_geoj(df, path):
    if os.path.exists(path):
        os.remove(path)
    df.to_file(path, driver="GeoJSON")

