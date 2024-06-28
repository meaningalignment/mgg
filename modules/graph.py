import json
from typing import List
from uuid import uuid4 as uuid
from prisma import Prisma, Json
from prisma.enums import ProcessState
from utils import serialize
import networkx as nx


class ValuesData:
    """
    Represents the data associated with a value in the moral graph.

    Attributes:
        title (str): The title of the value.
        policies (List[str]): A list of policies associated with the value.
        choice_context (str): The context in which the choice is made.
    """

    def __init__(self, title: str, policies: List[str], choice_context: str):
        self.title = title
        self.policies = policies
        self.choice_context = choice_context


class Value:
    """
    Represents a value node in the moral graph.

    Attributes:
        data (ValuesData): The data associated with the value.
        id (str): The unique identifier for the value.
    """

    def __init__(self, data: ValuesData, id: str | None = None):
        self.data = data
        self.id = id if id else str(uuid())


class EdgeMetadata:
    """
    Represents metadata associated with an edge in the moral graph.

    Attributes:
        story (str): The story associated with the edge.
        context_shifts (str): Context shifts associated with the edge.
        problem (dict): The problem associated with the edge.
        improvements (List[dict]): Improvements associated with the edge.
    """

    def __init__(
        self,
        story: str,
        context_shifts: str,
        problem: dict,
        improvements: List[dict],
    ):
        self.context_shifts = context_shifts
        self.improvements = improvements
        self.problem = problem
        self.story = story


class Edge:
    """
    Represents an edge in the moral graph.

    Attributes:
        from_id (str): The ID of the starting node.
        to_id (str): The ID of the ending node.
        context (str): The context of the edge.
        metadata (EdgeMetadata | None): The metadata associated with the edge.
    """

    def __init__(
        self,
        from_id: str,
        to_id: str,
        context: str,
        metadata: EdgeMetadata | None = None,
    ):
        self.from_id = from_id
        self.to_id = to_id
        self.context = context
        self.metadata = metadata


class MoralGraph:
    """
    Represents a moral graph consisting of values and edges.

    Attributes:
        values (List[Value]): A list of value nodes in the graph.
        edges (List[Edge]): A list of edges in the graph.
        seed_questions (List[str]): A list of seed questions for the graph.
    """

    def __init__(
        self,
        values: List[Value] = [],
        edges: List[Edge] = [],
        seed_questions: List[str] = [],
    ):
        self.values = values
        self.edges = edges
        self.seed_questions = seed_questions

    def get_winning_values(self, context: str, n_values: int = 1):
        """Get `n` the winning values for the context."""

        edges = [e for e in self.edges if e.context in context]
        values = [
            v
            for v in self.values
            if v.id in [e.from_id for e in edges] or v.id in [e.to_id for e in edges]
        ]
        trimmed_graph = MoralGraph(values, edges)

        # Get n winning value(s) by calculating PageRank score.
        n_values = 1
        pr = nx.pagerank(trimmed_graph.to_nx_graph())
        winning_value_ids = [
            p[0]
            for p in sorted(pr.items(), key=lambda x: x[1], reverse=True)[:n_values]
        ]
        return [v for v in values if v.id in winning_value_ids]

    def to_json(self):
        """
        Serializes the moral graph to a JSON-compatible dictionary.

        Returns:
            dict: The serialized moral graph.
        """
        return serialize(self)

    def to_nx_graph(self):
        """
        Converts the moral graph to a NetworkX directed graph.

        Returns:
            nx.DiGraph: The NetworkX directed graph.
        """
        G = nx.DiGraph()

        for value in self.values:
            G.add_node(
                value.id,
                title=value.data.title,
                policies=value.data.policies,
                choice_context=value.data.choice_context,
            )

        for edge in self.edges:
            G.add_edge(
                edge.from_id, edge.to_id, context=edge.context, metadata=edge.metadata
            )

        return G

    @classmethod
    def from_file(cls, path):
        """
        Creates a MoralGraph instance from a JSON file.

        Args:
            path (str): The path to the JSON file.

        Returns:
            MoralGraph: The created MoralGraph instance.
        """
        with open(path, "r") as f:
            data = json.load(f)
        return cls.from_json(data)

    @classmethod
    def from_json(cls, data):
        """
        Creates a MoralGraph instance from a JSON-compatible dictionary.

        Args:
            data (dict): The JSON-compatible dictionary.

        Returns:
            MoralGraph: The created MoralGraph instance.
        """
        values = [
            Value(id=v["id"], data=ValuesData(**v["data"])) for v in data["values"]
        ]
        edges = [
            Edge(
                **{k: v for k, v in e.items() if k != "metadata"},
                metadata=EdgeMetadata(**e["metadata"]),
            )
            for e in data["edges"]
        ]
        seed_questions = data.get("seed_questions", [])
        return cls(values, edges, seed_questions)

    @classmethod
    def from_db(cls, dedupe_id: int | None = None):
        """
        Creates a MoralGraph instance from a database.

        Args:
            dedupe_id (int | None): The deduplication ID. If None, the latest deduplication is used.

        Returns:
            MoralGraph: The created MoralGraph instance.
        """
        db = Prisma()
        db.connect()

        if not dedupe_id:
            dedupe = db.deduplication.find_first(order={"createdAt": "desc"})
            if not dedupe:
                raise ValueError("No deduplication found in db")
            dedupe_id = dedupe.id

        values = db.deduplicatedcard.find_many(where={"deduplicationId": dedupe_id})
        edges = db.deduplicatededge.find_many(where={"deduplicationId": dedupe_id})

        values = [Value(ValuesData(v.title, v.policies, ""), str(v.id)) for v in values]
        edges = [
            Edge(
                str(e.fromId),
                str(e.toId),
                e.contextName,
                (
                    EdgeMetadata(
                        **json.loads(json.dumps(dict(e.metadata)))
                    )  # Avoid Prisma Json type complaint.
                    if e.metadata
                    else None
                ),
            )
            for e in edges
        ]

        return cls(values, edges)

    def save_to_file(self, path: str | None = None):
        """
        Saves the moral graph to a JSON file.

        Args:
            path (str | None): The path to the JSON file. If None, a default path is used.
        """
        with open(path if path else f"./graph_{self.__hash__()}.json", "w") as f:
            json.dump(self.to_json(), f, indent=2)

    def save_to_db(self, generation_id: int | None = None):
        """
        Saves the moral graph to a database.

        Args:
            generation_id (int | None): The generation ID. If None, a new generation is created.
        """
        db = Prisma()
        db.connect()
        # git_commit = os.popen("git rev-parse HEAD").read().strip() TODO: fix this
        if not generation_id:
            generation_id = db.generation.create({"gitCommitHash": "foobar"}).id

        print("Adding values to db, in batches of 1000")
        for i in range(0, len(self.values), 1000):
            batch = self.values[i : i + 1000]
            db.valuescard.create_many(
                [
                    {
                        "title": value.data.title,
                        "policies": value.data.policies,
                        "generationId": generation_id,
                        "choiceContext": value.data.choice_context,
                    }
                    for value in batch
                ],
            )

        # map the db values to their corresponding uuids, so we can link our edges to them
        db_values = db.valuescard.find_many(
            where={"generationId": generation_id}, order={"id": "asc"}
        )
        uuid_to_id = {v.id: dbv.id for v, dbv in zip(self.values, db_values)}

        print("Adding edges to db, linking to values and contexts")
        for i in range(0, len(self.edges), 1000):
            batch = self.edges[i : i + 1000]
            db.edge.create_many(
                [
                    {
                        "fromId": uuid_to_id[edge.from_id],
                        "toId": uuid_to_id[edge.to_id],
                        "metadata": Json({**dict(serialize(edge.metadata))}),
                        "contextName": edge.context,
                        "generationId": generation_id,
                    }
                    for edge in batch
                ],
                skip_duplicates=True,
            )

        # mark the generation as finished
        db.generation.update(
            {"state": ProcessState.FINISHED}, where={"id": generation_id}
        )
        db.disconnect()
        print(f"Saved graph to db with generation id {generation_id}")
