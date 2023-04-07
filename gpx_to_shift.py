import argparse
import calendar
import csv
import datetime
import logging
from collections import OrderedDict
import os
import pandas as pd
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

import fiona
from shapely import geos, wkb
from shapely.geometry import shape
import gpxpy

def transform(file_name,out_file,l,index):
    """Creates a CSV file with EWKB geometries. 
    It will write the SRID (EPSG code) only if it is defined in the input file CRS. 
    :param file_name: Input file in one of the supported geospatial formats
    :return: Returns the path to the transformed file
    """

    
    with fiona.open(filename.path, layer=l) as source:
        if 'init' in source.crs.keys():
            epsg = int(source.crs['init'].split(':')[1])   
            print(epsg)       
            geos.WKBWriter.defaults['include_srid'] = True
            #print(source)

            with open(out_file, "w") as file:
                writer = csv.writer(file, delimiter=",", lineterminator="\n")
                firstRow = True
                for f in source:
                
                    try:
                        if firstRow:
                            writer.writerow(
                                ['geomEWKB'] + ['id'] + ['fileid'] +
                                list(f["properties"].keys())
                            )
                            firstRow = False
                        if epsg != -1:
                            writer.writerow(
                                [wkb.dumps(shape(f["geometry"]), hex=True, srid=epsg)] + [f['id']] + [index] +
                                list(f["properties"].values())
                            )
                        else:
                            writer.writerow(
                                [wkb.dumps(shape(f["geometry"]), hex=True)] + [f['id']] + [index] +
                                list(f["properties"].values())
                            )
                    except Exception:
                        logging.exception("Error processing feature %s:", f["id"])

                        break
    return out_file

def upload_file_s3(file_name, bucket):
    """Upload a file to an S3 bucket
    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :return: True if file was uploaded, else False
    """

    s3_client = boto3.client('s3')
    try:
        response = s3_client.upload_file(file_name, bucket, file_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True

def execute_redshift_statement(cluster_identifier, database, secret_arn, sql):
    """Executes a SQL statement on Redshift
    :param cluster_identifier: Redshift cluster
    :param database: Redshift database where the statement will be executed
    :param secret_arn: ARN of the secret that enables access to the database
    :param sql: SQL statement to execute
    :return: List of records
    """

    client = boto3.client('redshift-data')
    try:
        # Execute the SQL statement
        query_response = client.execute_statement(
            ClusterIdentifier=cluster_identifier,
            Database=database,
            SecretArn=secret_arn,
            Sql=sql
        )

        # Wait until execution finishes
        result_status_response = client.describe_statement(
            Id=query_response['Id']
        )
        while result_status_response['Status'] != 'FAILED' and result_status_response['Status'] != 'FINISHED':
            result_status_response = client.describe_statement(
                Id=query_response['Id']
            )
        
        # Process results
        if result_status_response['Status'] == 'FAILED':
            raise Exception('Error executing SQL statement: ' + sql + '\n' + result_status_response['Error'])

        # Check if there is a result set
        if result_status_response['Status'] == 'FINISHED':
            if result_status_response['HasResultSet']:
                result_response = client.get_statement_result(
                    Id=query_response['Id']
                )
                result = result_response['Records']
                while result_response['NextToken'] != "":
                    result_response = client.get_statement_result(
                        Id=query_response,
                        NextToken=result_response['NextToken']
                    )
                    result = result + result_response['Records']
                return result
            else:
                return []
    except ClientError as e:
        logging.error(e)
        return False
    return True

def get_field_mappings(schema):
    """Maps Fiona data types to Redshift data types for each in the schema
    :param schema: Fiona schema
    :return: Dictionary with the data type for each field
    """
    field_mappings = OrderedDict()
    for property in schema['properties']:
        property_type = fiona.prop_type(schema['properties'][property])
        if property_type == type(int()):
            # Redshift data types: INTEGER, BIGINT
            field_mappings[property] = 'BIGINT'
        elif property_type == type(float()):
            # Redshift data types: REAL, DOUBLE PRECISION
            field_mappings[property] = 'DOUBLE PRECISION'
        elif property_type == type(str()):
            length = fiona.prop_width(schema['properties'][property])
            field_mappings[property] = 'VARCHAR({0})'.format(length)
        elif property_type == type(bool()):
            field_mappings[property] = 'BOOLEAN'
        elif "FionaDateType" in str(property_type):
            field_mappings[property] = 'DATE'
        elif "FionaTimeType" in str(property_type):
            field_mappings[property] = 'TIME'
        elif "FionaDateTimeType" in str(property_type):
            field_mappings[property] = 'TIMESTAMP'
        else:
            # If it is a different type, we will use VARCHAR(MAX)
            field_mappings[property] = 'VARCHAR(MAX)'

    return field_mappings    


def get_create_table_statement(file_name, table_name):
    """Gets the SQL CREATE TABLE statement from the input file schema
    :param file_name: Input file
    :param table_name: Name of the table that will be created
    :return: CREATE TABLE statement
    """
    with fiona.open(file_name, "r") as source:
        schema = source.schema

    field_mappings = get_field_mappings(schema)
    fields = "geom GEOMETRY, ";
    for field in field_mappings:
        fields += field + " " + field_mappings[field] + ", "
    fields = fields[:-2]  # Remove the last ", "

    statement = "CREATE TABLE {0}({1})".format(table_name, fields)
                
    return statement

def import_file_redshift(original_file_name, 
                         csv_file_path, 
                         cluster_identifier, 
                         database,
                         table_name, 
                         secret_arn,
                         redshift_role_arn):
    """Import a CSV file into Redshift with EWKB geometries using COPY
    :param file_name: CSV file to import
    :param csv_file_path: S3 path where the CSV file is located
    :param cluster_identifier: Redshift cluster
    :param database: Redshift database where the data will be imported
    :param table_name: Redshift table where the data will be imported
    :param secret_arn: ARN of the secret that enables access to the database
    :param redshift_role_arn: ARN of the Redshift role with read access to S3
    :return: True if file was imported, else False
    """

    try:
        # Create table
        result = execute_redshift_statement(
            cluster_identifier, 
            database,
            secret_arn, 
            get_create_table_statement(original_file_name, table_name)
        )
        # Load the data using COPY
        result = execute_redshift_statement(
            cluster_identifier, 
            database,
            secret_arn, 
            ("COPY {0} FROM '{1}' " 
             "IAM_ROLE '{2}' "
             "FORMAT CSV IGNOREHEADER 1 "
             "TIMEFORMAT 'YYYY-MM-DDTHH:MI:SS';").format(table_name, csv_file_path, redshift_role_arn)
        )
    except Exception as e:
        logging.error(e)
        return False
    return True


#def main(input_directory, bucket, cluster_identifier, database, secret_arn, redshift_role_arn):


if __name__ == "__main__":

    
    input_directory='GPX-tracks'
    dir_tracks='tracks'
    dir_track_points='track_points'
    upload_data='data'
    
    ##tranform data for redshift into EWKB
    i=0
    for filename in os.scandir(input_directory):
        if filename.is_file():
            tracks=r'tracks\tracks'+str(i)+'.csv'
            points=r'track_points\track_points'+str(i)+'.csv'
           
            csv_file = transform(filename.path,tracks,'tracks',i)
            csv_file2 = transform(filename.path,points,'track_points',i)

            i=i+1
            print("CSV file created with geometries in EWKB format.")
    

    # list the path of all the csv created & load it into a dataframe
    csv_traks = [file for file in Path(dir_tracks).glob('*')]
    single_tracks = pd.concat([pd.read_csv(f) for f in  csv_traks], ignore_index=True)

    csv_trak_points = [file for file in Path(dir_track_points).glob('*')]
    single_track_points = pd.concat([pd.read_csv(f) for f in  csv_trak_points], ignore_index=True)

    single_tracks.to_csv(r'data\tracks.csv')
    single_track_points.to_csv(r'data\track_points.csv')

    
'''
    ### UPLOAD ON S3 AND THEN ON REDSHIFT
    for filename in os.scandir(upload_data):
        if filename.is_file():

            table_name = os.path.basename(filename).split('.')[0]
 
            if upload_file_s3(csv_file, bucket):
                print("File uploaded to S3.")
                if import_file_redshift(
                    input_file,
                    "s3://{0}/{1}".format(bucket, csv_file),
                    cluster_identifier,
                    database,
                    table_name,
                    secret_arn,
                    redshift_role_arn):
                    print("Data loaded to Redshift.")
                else:
                    print("Error loading data to Redshift.")
            else:
                print("Error uploading file to S3.")
'''

