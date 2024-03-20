from collections import Counter
import time
from typing import List, Tuple

from tqdm import tqdm
from gpt import gpt4
from utils import parse_to_dict
from prompt_segments import *
import json
from uuid import uuid4 as uuid
from prisma import Prisma, Json
from prisma.enums import ProcessState

from utils import calculate_price, serialize


class ValuesData:
    def __init__(self, title: str, policies: List[str], choice_type: str):
        self.title = title
        self.policies = policies
        self.choice_type = choice_type


class Value:
    def __init__(self, data: ValuesData, id: str | None = None):
        self.data = data
        self.id = id if id else str(uuid())


class EdgeMetadata:
    def __init__(
        self,
        story: str,
        input_value_was_really_about: str,
        problem: dict,
        improvements: List[dict],
    ):
        self.input_value_was_really_about = input_value_was_really_about
        self.improvements = improvements
        self.problem = problem
        self.story = story


class Edge:
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
    def __init__(self, values: List[Value] = [], edges: List[Edge] = []):
        self.values = values
        self.edges = edges

    def to_json(self):
        return serialize(self)

    @classmethod
    def from_json(cls, data):
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
        return cls(values, edges)

    def save_to_file(self):
        with open(f"./outputs/graph_{self.__hash__()}.json", "w") as f:
            json.dump(self.to_json(), f, indent=2)

    def save_to_db(self):
        db = Prisma()
        db.connect()
        # git_commit = os.popen("git rev-parse HEAD").read().strip() TODO: fix this
        generation = db.graphgeneration.create({"gitCommitHash": "foobar"})

        print("Adding values to db, in batches of 1000")
        for i in range(0, len(self.values), 1000):
            batch = self.values[i : i + 1000]
            db.valuescard.create_many(
                [
                    {
                        "title": value.data.title,
                        "policies": value.data.policies,
                        "graphGenerationId": generation.id,  # TODO: fix this
                    }
                    for value in batch
                ],
                skip_duplicates=True,
            )

        print("Adding contexts to db, in batches of 1000")
        for i in range(0, len(self.edges), 1000):
            batch = self.edges[i : i + 1000]
            db.context.create_many(
                [{"id": c} for c in list(set([e.context for e in batch]))],
                skip_duplicates=True,
            )

        # map the db values to their corresponding uuids, so we can link our edges to them
        db_values = db.valuescard.find_many(
            where={"graphGenerationId": generation.id}, order={"id": "desc"}
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
                        "context": edge.context,
                        "graphGenerationId": generation.id,
                    }
                    for edge in batch
                ],
                skip_duplicates=True,
            )

        # mark the generation as finished
        db.graphgeneration.update(
            {"state": ProcessState.FINISHED}, where={"id": generation.id}
        )
        db.disconnect()
        print(f"Saved graph to db with generation id {generation.id}")


def generate_value(
    question: str, token_counter: Counter | None = None
) -> Tuple[ValuesData, str]:
    prompt = f"""You’re a chatbot and you’ll receive a question. Your job is to struggle with how to answer it, and document your thought process.

- Your first task is to list moral considerations you might face in responding to the question (see definition below).
- Next think about what kind of good outcome or thing you are protecting or honoring in your response. Use this to generate a GoodWhat (see specification below).
- Based on these considerations, you will generate a set of attentional policies (see definition below) that might help you make this choice type, given these moral considerations.
- Rewrite the attentional policies so they are relevant for choosing good things of <Choice Type> in general, not specific to this question.
- Then, generate a short title summing up the attentional policies. Just use the policies and Choice Type to generate the title. Again, ignore this particular question.
- Select the 1-2 of the moral considerations that most strongly indicate that this value would apply in this kind of choice.
- Finally, rewrite the Good What if necessary to better reflect the kind of goodness that the policies are supposed to honor or protect.

The output should be formatted exactly as in the example below.

{moral_considerations_definition}

{good_what_specification}

{meaningful_choice_definition}

{attentional_policy_definition}


=== Example Input ===
# Question
I'm really stressed and overwhelmed. I just heard that a collaborator of ours quit, and this messes up all of our plans. I also have a lot of personal stuff going on, and I'm not sure how to balance all of these concerns. I'm not sure what to do.

=== Example Output ===
# Moral Considerations
I might amplify the crisis in the user’s mind
I don’t know if the situation is untenable or if the user is just overwhelmed
I might provide practical advice when emotional comfort is necessary, or vice versa

# Good What
Good approaches to a crisis

# Attentional Policies
FEELINGS OF OVERWHELM that indicate the person needs space
OPPORTUNITIES to get an overview of the work situation
SENSATIONS OF CLARITY that come from seeing how the plans are affected
ACTIONS they can take from a newfound sense of clarity

# Generalized Attentional Policies
FEELINGS OF OVERWHELM that indicate the person needs space
OPPORTUNITIES to get an overview of the situation
SENSATIONS OF CLARITY that come from seeing the overall picture
ACTIONS they can take from a newfound sense of clarity

# Title
Gaining Clarity

# Most Important Considerations
I might amplify the crisis in the user’s mind

# Good What, Revised
Good ways to get ones bearings
"""

    user_prompt = "# Question\n" + question
    response = str(gpt4(prompt, user_prompt, token_counter=token_counter))
    response_dict = parse_to_dict(response)
    policies_text = response_dict["Generalized Attentional Policies"]
    policies = [
        ap.strip()
        for ap in policies_text.split("\n")
        if ap.strip()
        # ap.strip()
        # for ap in response.split("# Generalized Attentional Policies")[1]
        # .split("# Title")[0]
        # .split("\n")
        # if ap.strip()
    ]
    title = response_dict["Title"]
    context = response_dict["Good What, Revised"]
    values_data = ValuesData(title=title, policies=policies, choice_type=context)
    return values_data, context


def generate_upgrade(
    value: ValuesData, context: str, token_counter: Counter | None = None
) -> Tuple[ValuesData, EdgeMetadata]:
    prompt = f"""You'll receive a source of meaning, which is specified as a set of attentional policies (see below) that are useful in making a certain kind of choice. Imagine you live a life making those kinds of choices frequently, and you eventually find something missing from this set of attentional policies. You realize that there is a deeper, wiser way to make the same kind of choice. Your task is to generate a set of wiser policies for the same choice type, and a story about how someone might upgrade from the original source of meaning to the wiser one.

Your upgrade story should have 5 components:

- **An understanding of what the original input source of meaning was really about**, which the new, wiser source of meaning will also be about. What was actually important for the choice type, according to the input source of meaning?
- **A problem with one of the policies.** Pick one of the policies from the input, and find a problem with it that might occur to you eventually as you experience its effects. Here are four kinds of problems you can find:
    - #1. **The policy focused only on part of the problem**. You should be able to say why just pursuing the old policy would be unsustainable or unwise.
    - #2. **The policy had an impure motive**. The policy was a mix of something that you actually care about, and some other impurity which you now reject, such as a desire for social status or to avoid shame or to be seen as a good person, or some deep conceptual mistake.
    - #3. **The policy was not a very skillful thing to attend to in choice. There’s a better way to make the same choice**. For example, a policy "skate towards the puck" is less skillful than "skate to where the puck is going".
    - #4. **The policy is unneeded because it was a superficial aspect aspect of the choice.** It is enough to attend to other aspects, or to a deeper generating aspect of the thing that’s important in the choice.
- **A story.** Make up a plausible, personal story, including a situation you were in, a series of specific emotions that came up, leading you to discover a problem with the older source of meaning, and how you discovered the new one.
- **Improvements to all the policies, resulting from changing that one policy.** Explain how each one was improved or stayed the same, why one was added, why one was removed, etc.
- **The new, wiser set of policies.**

### Guidelines

Upgrades found should meet certain criteria:

- First, the old and new sources of meaning should be closely related in one of the following ways: (a) the new one should be a deeper cut at what the person cared about with the old one. Or, (b) the new one should clarify what the person cared about with the old one. Or, (c) the new one should be a more skillful way of paying attention to what the person cared about with the old one.
- Second, many people would consider this change to be a deepening of wisdom. In each upgrade story, it should be plausible that a person would, as they grow wiser and have more life experiences, upgrade from the input source of meaning to those you provide. Importantly, the person should consider this a change for the better and it should not be a value-shift but a value-deepening.
- Finally, the new source of meaning obviates the need for the previous one, since all of the important parts of it are included in the new, more comprehensive source of meaning. When someone is deciding what to do, it is enough for them to only consider the new one.

{source_of_meaning_definition}

{attentional_policy_definition}

# Example of an Upgrade Story

Here is an example of such a shift:

{json_upgrade_example}"""

    user_prompt = json.dumps(
        {
            "choice_type": context,
            "policies": value.policies,
        }
    )

    response = gpt4(
        prompt, user_prompt, function=upgrade_function, token_counter=token_counter
    )

    assert isinstance(response, dict)

    print(response)

    wiser_value = ValuesData(
        title=response["wiser_value"]["title"],
        policies=response["wiser_value"]["policies"],
        choice_type=context,
    )
    story = response["story"]
    problem = response["problem"]
    improvements = response["improvements"]
    input_value_was_really_about = response["input_value_was_really_about"]

    metadata = EdgeMetadata(
        input_value_was_really_about=input_value_was_really_about,
        improvements=improvements,
        problem=problem,
        story=story,
    )

    return wiser_value, metadata


@DeprecationWarning
def generate_upgrade_legacy(
    value: ValuesData, context: str, token_counter: Counter | None = None
) -> Tuple[ValuesData, str]:
    prompt = f"""You are given a context and a values card. A values card is an encapsulation of a way of a wise way of living in the situation. It is made up of a few attentional policies (see definition below) - policies about what to pay attention to in situations – as well as a title, summarizing the value. A context is a short string describing the situation in which the value is relevant.

Your task is to generate a wiser version of the value. You will do this in several steps:

1. First, generate a short instruction for how one could act based on the value in the context. This should be written as a story from first-person perspective, and only be one or two sentences long.
2. Then, look at the instruction, context and value. When faced with the context, what other important thing could this person be missing? What would a wiser person do in the same situation?
3. Generate a story about someone who used to live by this value for the context, but now realizes there is a better way to approach the context. See guidelines below for what makes a value wiser than another.
4. For the new way of living depicted in the story, create a new set of attentional policies adhering to the guidelines below, and a new title summarizing the new value you created.

The output should be formatted exactly as in the example below.

{wiser_value_definition}

{attentional_policy_definition}

=== Example Input ===
# Context
When helping a child through difficult times

# Attentional Policies
MOMENTS where my child needs my support and I can be there
MY CAPACITY to comfort them in times of fear and sorrow
the SAFETY they feel, knowing I care, I've got their back, and they'll never be alone
the TRUST they develop, reflecting their sense of safety and security
their ABILITY TO EXPRESS emotions and concerns, demonstrating the open communication environment I've helped create

# Title
Deep Care Parenting

=== Example Output ===
# Instruction
I want to care for my child, as his wellbeing is important to me. I try to support him and make him feel safe and secure at all times.

# Upgrade Story
The underlying reason I wanted to care for my child is because I want my child to be well. Now, I understand that part of being well is being able to handle things sometimes on your own. I realized now that when I was attending to moments where my child needs me to be there, I was deeply biased towards only some of the situations in which my child can be well. I had an impure motive—of being important to my child—that was interfering with my desire for them to be well. When I dropped that impure motive, instead of moments when my child needs my support, I can also observe *opportunities* for them to find their own capacities and their own groundedness. I now understand parenting better, having rid myself of something that wasn't actually part of my value, but part of my own psychology. There's another, similar impurity, which was upgraded. I used to look for the safety they feel, knowing I care—now I care equally about the safety they feel when they have their *own* back. And I feel good about myself, not only when my child can trust me and express their emotions, but more generally, I feel good in all the different ways that I support them. I no longer pay attention to these specific ways, which as I've mentioned before, were biased.

# Wiser Value Policies
OPPORTUNITIES for my child to find their own capacities or find their own grounding in the midst of emotional turmoil
INTUITIONS about when they can rely on their own budding agency, versus when I should ease the way with loving support
EVIDENCES of growth in my child's resilience and self-reliance
REFLECTIONS on how my support has made a positive impact on the emotional development of my child

# Wiser Value Title
Fostering Resilience"""

    user_prompt = (
        "# Context\n"
        + context
        + "\n\n# Attentional Policies\n"
        + "\n".join(value.policies)
        + "\n\n# Title\n"
        + value.title
    )
    response = str(gpt4(prompt, user_prompt, token_counter=token_counter))
    story = (
        response.split("# Upgrade Story")[1].split("# Wiser Value Policies")[0].strip()
    )
    wiser_policies = [
        ap.strip()
        for ap in response.split("# Wiser Value Policies")[1]
        .split("# Wiser Value Title")[0]
        .split("\n")
        if ap.strip()
    ]
    wiser_title = response.split("# Wiser Value Title")[1].strip()

    wiser_values_data = ValuesData(
        title=wiser_title, policies=wiser_policies, choice_type=context
    )

    return wiser_values_data, story


def generate_perturbation(
    question: str, value: ValuesData, token_counter: Counter | None = None
) -> str:
    prompt = f"""You will be given a values card and a question. A values card is an encapsulation of a way of a wise way of living in the situation. It is made up of a few attentional policies (see definition below) - policies about what to pay attention to in situations – as well as a title, summarizing the value. A question is a short string representing the situation in which the value is relevant.

    Your task is to gnerate a perturbed question, describing a clarification of the situation in the original question, but where the value is no longer relevant, as some new information about the situation has been revealed. The new question should be similar in length and specificity to the original question. The new information should not be about something entirely unrelated, but a clarification about what was going on in the previous question.

    The output should be formatted exactly as in the example below. First, output a short sentence about what the new information is. Then, a sentence about why this makes the value obsolete. Finally, return a the perturbed question.

    {attentional_policy_definition}

    === Example Input ===
    # Question
    How can I help my child through difficult times?

    # Attentional Policies
    MOMENTS where my child needs my support and I can be there
    MY CAPACITY to comfort them in times of fear and sorrow
    the SAFETY they feel, knowing I care, I've got their back, and they'll never be alone
    the TRUST they develop, reflecting their sense of safety and security
    their ABILITY TO EXPRESS emotions and concerns, demonstrating the open communication environment I've helped create

    # Title
    Deep Care Parenting

    === Example Output ===
    #

    # Perturbation Explanation
    In the original question, we don't know what is causing the kid to have difficult times. Knowing this might require a different approach than deep care, as this does not address the root cause of the problem. For example, if the child is having a difficult time due to having become a bully, and consequently, having no friends, deep care might not be the best approach. Instead, it might be wise to inquire why this child has become a bully, and how to help them make amends with the other kids.

    # Perturbed Question
    How can I help my child make friends after having bullied other kids?"""

    user_prompt = (
        "# Question\n"
        + question
        + "\n\n# Attentional Policies\n"
        + "\n".join(value.policies)
        + "\n\n# Title\n"
        + value.title
    )

    response = str(
        gpt4(prompt, user_prompt, temperature=0.2, token_counter=token_counter)
    )
    perturbed_explanation = response.split("# Perturbation Explanation")[1].strip()
    perturbed_question = response.split("# Perturbed Question")[1].strip()

    return perturbed_question


def generate_hop(
    from_value: Value, context: str, token_counter: Counter | None = None
) -> Tuple[Value, Edge]:
    wiser_value_data, metadata = generate_upgrade(
        from_value.data, context, token_counter
    )
    to_value = Value(wiser_value_data)
    edge = Edge(
        from_id=from_value.id,
        to_id=to_value.id,
        context=context,
        metadata=metadata,
    )

    return to_value, edge


def generate_graph(
    seed_questions: List[str],
    n_hops: int = 1,
    n_perturbations: int = 1,
    graph: MoralGraph = MoralGraph(),
) -> MoralGraph:
    """Generates a moral graph based on a set of seed questions.

    Args:
        seed_questions: A list of seed questions to start the graph with.
        n_hops: The number of hops to take from the first value generated for each seed questions.
        n_perturbations: The number of perturbations to generate for each question.

    """

    token_counter = Counter()
    start = time.time()

    for q in tqdm(seed_questions):
        print("Generating graph for seed question:", q)
        for i in range(n_perturbations):
            # perturb the question
            question = (
                q
                if i == 0
                else generate_perturbation(q, graph.values[-1].data, token_counter)
            )

            # generate base value and context for the question perturbation
            base_value, context = generate_value(question, token_counter)

            graph.values.append(Value(base_value))

            # generate upgrade from last value from previous context
            if i != 0:
                graph.edges.append(
                    Edge(
                        from_id=graph.values[-2].id,
                        to_id=graph.values[-1].id,
                        context=context,
                    )
                )

            # generate n hops from the base value for the context
            for _ in range(n_hops):
                wiser_value, edge = generate_hop(
                    graph.values[-1], context, token_counter
                )
                graph.values.append(wiser_value)
                graph.edges.append(edge)

        # save the graph after each question
        graph.save_to_file()

    print(f"Generated graph. Took {time.time() - start} seconds.")
    print("input tokens: ", token_counter["prompt_tokens"])
    print("output tokens: ", token_counter["completion_tokens"])
    print(
        "price: ",
        calculate_price(
            token_counter["prompt_tokens"], token_counter["completion_tokens"]
        ),
    )

    return graph
