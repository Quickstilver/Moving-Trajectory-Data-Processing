# Moving-Trajectory-Data-Processing-and-Visualization


This project is a comprehensive solution to process, clean, smooth, and visualize moving trajectory data using powerful Python libraries like Pandas, Geopandas, Movingpandas, and Holoviews. The project focuses on the following tasks:

- Reads in the data stored in a .csv file located in the "data" directory
- Cleans the data by filtering out trajectories on land using the Basemap library
- Creates a TrajectoryCollection object from the cleaned data using Movingpandas
- Applies a Kalman filter to the trajectories in the collection to smooth them out
- Visualizes the original and smoothed trajectories using Holoviews
- Performs additional cleaning and smoothing on a single trajectory

## Preprocessing 
The project includes a preprocessing script that imports, transforms, and processes geospatial data.
The script can also be extended to upload the data to S3 and then load it into Redshift.

## Data visualization and smoothing
The accompanying Jupyter Notebook demonstrates the entire process of cleaning and smoothing the trajectories using various techniques, as well as visualizing the original and processed trajectories in an interactive and appealing manner.

![ezgif com-crop](https://user-images.githubusercontent.com/28387807/230591767-f75a3868-4187-4a10-97ed-bb3e455ebd3e.gif)


## Conclusions

This project serves as an excellent showcase of using data science and geospatial libraries to process and visualize complex data while maintaining an easy-to-understand and visually appealing presentation.
