import pandas as pd
from neo4j import GraphDatabase, Transaction

from myapp.graph_creation import yml

cfg: dict = yml.get_cfg("neo4j")

URL = cfg.get("url")
USER = cfg.get("user")
PASS = cfg.get("password")
FILE = cfg.get("file")


def read_graph_data(file_name: str) -> pd.DataFrame:
    target_cols = ["Идентификатор операции", "Артикул", "Название операции", "Последователи"]
    df = pd.read_excel(file_name, dtype=str)
    exist_cols = df.columns.values.tolist()
    if "ADCM_П/п" in exist_cols:
        df.rename(columns={"ADCM_П/п": "Артикул"}, inplace=True)

    df = df[target_cols]
    df = df.loc[df["Артикул"].notna()]
    df.loc[:, "Идентификатор операции"] = df["Идентификатор операции"].apply(str.strip)
    df = df[df["Идентификатор операции"].str.startswith("R")]
    df.set_index("Идентификатор операции", inplace=True)  # Update indeces

    return df


def make_graph(tx: Transaction, data: pd.DataFrame):
    id_lst = data.index.tolist()
    for wrk_id in id_lst:
        tx.run(
            "MERGE (a:Work {id: $id}) " "SET a.name = $name",
            id=data.loc[wrk_id, "Артикул"],
            name=data.loc[wrk_id, "Название операции"],
        )

        s = data.loc[wrk_id, "Последователи"]
        if s == s:  # Проверка на то, что есть Последователи (s != NaN)
            followers = s.split(", ")
            for flw_id in followers:
                if flw_id in id_lst:  # Создаем ребра только к вершинам, описанным в таблице отдельной строкой
                    tx.run(
                        "MATCH (a:Work) WHERE a.id = $wrk_id "
                        "MERGE (flw:Work {id: $flw_id}) "
                        "SET flw.name = $flw_name "
                        "MERGE (a)-[r:FOLLOWS]->(flw) "
                        "SET r.weight = coalesce(r.weight, 0) + 1",
                        wrk_id=data.loc[wrk_id, "Артикул"],
                        flw_id=data.loc[flw_id, "Артикул"],
                        flw_name=data.loc[flw_id, "Название операции"],
                    )


def clear_database(tx: Transaction):
    tx.run("MATCH (n) " "DETACH DELETE n")


def main(file=FILE):  # Проверяй базу данных database= d

    data = read_graph_data(file)
    driver = GraphDatabase.driver(URL, auth=(USER, PASS))
    with driver.session() as session:
        session.write_transaction(make_graph, data)
    driver.close()


if __name__ == "__main__":
    main()
