import json
import urllib.parse
import boto3
import pandas as pd
from io import StringIO
from datetime import date
import warnings

warnings.filterwarnings('ignore')

print('Loading function')

s3 = boto3.client('s3')


def sf_to_ac(x):
    if x > 2000:
        x = x / 43560
    return round(x, 2)


def lambda_handler(event, context):
    print("Received event: " + json.dumps(event, indent=2))

    # Get the object from the event and show its content type
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    print(key)

    df = extract(bucket, key)
    df = transform(df)
    load(df, key)
    print(df)


def extract(bucket, key):
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")

        if status == 200:
            print(f"Successful S3 get_object response. Status - {status}")
            estimate_df = pd.read_csv(response.get("Body"))
            print(estimate_df)
        else:
            print(f"Unsuccessful S3 get_object response. Status - {status}")
        return estimate_df
    except Exception as e:
        print(e)
        print(
            'Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as this function.'.format(
                key, bucket))
        raise e


def transform(df):
    # 1. Drop column
    df.drop('notes', axis=1, inplace=True)
    # 2. Drop Duplicates
    df = df.drop_duplicates(subset=['PROJECT_NAME'])
    # 3. Convert date col to date format and Date formatting as dd-mm-yyyy
    today = date.today()
    df['ESTIMATE_DUE_DATE'] = df[['ESTIMATE_DUE_DATE']].applymap(lambda x: x if isinstance(x, str) else today)
    df['ESTIMATE_DUE_DATE'] = df[['ESTIMATE_DUE_DATE']].replace(to_replace=["#REF!", '44519', '44722'],
                                                                value=today)
    df['ESTIMATE_DUE_DATE'] = df.ESTIMATE_DUE_DATE.apply(lambda x: pd.to_datetime(x).strftime('%m/%d/%Y'))
    # 4. cleaning spl char in str col

    df['PROJECT_NUMBER'] = df['PROJECT_NUMBER'].str.replace('-', '')
    df['PROJECT_NUMBER'] = df[['PROJECT_NUMBER']].applymap(lambda x: x if isinstance(x, str) else '')
    # 5. Converting unit types . remove acres in SW

    df['SITEWORK_AC'] = df['SITEWORK_AC'].str.replace(' ACRES', '')
    df['SITEWORK_AC'] = df['SITEWORK_AC'].fillna(0.0)
    df['SITEWORK_AC'] = df['SITEWORK_AC'].astype(float)
    df['SITEWORK_AC'] = df.SITEWORK_AC.apply(sf_to_ac)
    # 6.  string concatenation

    df["Address"] = df["CITY"].str.cat(df["STATE"], sep=", ")
    return df


def load(df, key):
    bucket = 'destini-estimator'  # already created on S3
    csv_buffer = StringIO()
    df.to_csv(csv_buffer)
    s3_resource = boto3.resource('s3')
    filename = 'transformed_data/' + key
    s3_resource.Object(bucket, filename).put(Body=csv_buffer.getvalue())

    #  import psycopg2

# def redshift():

#     conn = psycopg2.connect(dbname='database_name', host='888888888888****.u.****.redshift.amazonaws.com', port='5439', user='username', password='********')
#     cur = conn.cursor();

#     cur.execute("truncate table example;")

#     //Begin your transaction
#     cur.execute("begin;")
#     cur.execute("copy example from 's3://examble-bucket/example.csv' credentials 'aws_access_key_id=ID;aws_secret_access_key=KEY/KEY/pL/KEY' csv;")
#     ////Commit your transaction
#     cur.execute("commit;")
#     print("Copy executed fine!")

# redshift();