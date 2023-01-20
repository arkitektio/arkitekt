from arkitekt import easy
from mikro.api.schema import from_df
import seaborn as sns

app = easy("easy_iris")


if __name__ == "__main__":

    with app:
        # from _df takes any kind of pandas dataframe and converts it to a table on arkitekt
        # this table will be stored as a parquet file on the server and therefore supports 
        # lazy data acess
        table = from_df(sns.load_dataset("iris"), "johannes")

        # will print the same data as the dataframe (but 'streaming' from the server)
        print(table.data)