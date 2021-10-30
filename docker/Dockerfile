FROM python:3.9

RUN apt-get update && apt-get install tzdata unar gdal-bin libgdal-dev -y
RUN pip install --upgrade pip
RUN pip install geopandas scipy autopep8
RUN pip install GDAL==`gdal-config --version` --global-option=build_ext --global-option="-I/usr/include/gdal"
RUN pip install folium pydeck scikit-image numpy-stl mbutil
RUN apt-get install docker docker-compose -y
RUN apt-get install nodejs npm -y
