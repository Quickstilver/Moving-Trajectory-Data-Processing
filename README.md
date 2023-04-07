# Moving-Trajectory-Data-Processing-and-Visualization


This project is a comprehensive solution to process, clean, smooth, and visualize moving trajectory data using powerful Python libraries like Pandas, Geopandas, Movingpandas, and Holoviews. The project focuses on the following tasks:



## Preprocessing 
The project includes a preprocessing script that imports, transforms, and processes geospatial data.
The script can also be extended to upload the data to S3 and then load it into Redshift.

- Reads input geospatial files from the "GPX-tracks" data folder.
- Transforms the input geospatial files into CSV files with EWKB geometries using the transform() function.
- Stores the transformed CSV files in a new "data" folder.
- Concatenates the CSV files into single tracks and single track points dataframes.
- Optionally, the script can:

  - Upload the CSV files to an Amazon S3 bucket using the upload_file_s3() function.
  - Execute SQL statements on AWS Redshift using the execute_redshift_statement() function.
  - Map Fiona data types to Redshift data types using the get_field_mappings() function.
  - Generate a SQL CREATE TABLE statement based on the input file schema using the get_create_table_statement() function.
  - Import the CSV files into Redshift with EWKB geometries using the import_file_redshift() function.

## Data visualization and smoothing
The accompanying Jupyter Notebook demonstrates the entire process of cleaning and smoothing the trajectories using various techniques, as well as visualizing the original and processed trajectories in an interactive and appealing manner.

- Reads in the data stored in a .csv file located in the "GPX-tracks" directory
- Cleans the data by filtering out trajectories on land using the Basemap library
- Creates a TrajectoryCollection object from the cleaned data using Movingpandas
- Applies a Kalman filter to the trajectories in the collection to smooth them out
- Visualizes the original and smoothed trajectories using Holoviews
- Performs additional cleaning and smoothing on a single trajectory

![ezgif com-crop](https://user-images.githubusercontent.com/28387807/230591767-f75a3868-4187-4a10-97ed-bb3e455ebd3e.gif)


## Conclusions

This project serves as an excellent showcase of using data science and geospatial libraries to process and visualize complex data while maintaining an easy-to-understand and visually appealing presentation.
