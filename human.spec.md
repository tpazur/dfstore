dfstore

dfstore is a small tool which saves dataframes centrally. The user can give the dataframes a unique name , as well as descroption and tags and retrieve them later easily. Use cases are solo data sciensist which want
to store results of previous analysis tasks or static dataframes centrally. 

the tool should use  $HOME/.dfstore as default storage. 

Main Features : 

- Save dataframes with description and labels
 - dfstore.save(df,name,description='',tags={'version'})
- Save dataframe as parquet
- Store metadata for each dataframe save. shape,dtypes,null counts,describe etc.
- Versioning : If a dataframe is updated store , increase the version and store the difference in shape 
- Support pandas and polars
- List dataframes and search by description or tags
- Search a dataframe by version history
- Search dataframes by columns and index
- delete dataframes: Soft (deleted flag) or hard delete
- CLI : be able to do the dfstore operations on shell dfstore add/update/info/list etc
- GUI : dfstore serve creates a GUI to do the main operations

# Demo
import dfstore

## Save
mydf = pd.DataFrame({
    'name': ['Alice', 'Bob', 'Charlie'],
    'age': [25, 30, 35],
    'city': ['New York', 'Los Angeles', 'Chicago']
})

python : dfstore.save(mydf, name='mydf', description='Sample dataframe', tags=['demo',{'env': 'production'}])
CLI : dfstore save mydf --description "Sample dataframe" --tags demo --tags env=production

## Info
python : dfstore.info('mydf')
CLI : dfstore info mydf
# Output:
Name: mydf
Description: Sample dataframe
Tags: demo, env=production
Last Updated: 2024-06-01 
Version: 1
Shape: (3, 3)
Dtypes: name: object, age: int64, city: object

## Get
python : dfstore.get('mydf')
CLI : dfstore get mydf
# Output:
   name  age         city
0  Alice   25     New York
1    Bob   30  Los Angeles
2 Charlie   35      Chicago

## List
python : dfstore.list()
CLI : dfstore list
# Output:
Name    Description         Tags                Last Updated   Version Shape
mydf    Sample dataframe   demo, env=production 2024-06-01     1       (3, 3)

## Update
mydf['age'] = mydf['age'] + 1
dfstore.save(mydf, name='mydf', notes='Needed update', tags=['demo',{'env': 'production'}])

## Versioning
python : dfstore.versions('mydf')
CLI : dfstore versions mydf
# Output:
Version    Updated At          Notes
1          2024-06-01          Initial save
2          2024-06-02          Needed update

## Search
python : dfstore.search(description='Sample')
CLI : dfstore search --description "Sample"
# Output:
Name    Description         Tags                Last Updated   Version Shape
mydf    Sample dataframe   demo, env=production 2024-06-01     1       (3, 3)

## Column Search
python : dfstore.search(columns=['age'])
CLI : dfstore search --columns age
# Output:
Name    Description         Tags                Last Updated   Version Shape
mydf    Sample dataframe   demo, env=production 2024-06-01     1       (3, 3)
