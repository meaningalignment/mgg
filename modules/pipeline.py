from typing import List
from functions import gpt4
from prompt_segments import *


def generate_value(
    question: str,
) -> {"title": str, "policies": List[str], "context": str,}:
    prompt = f"""You will be given a question.  Your first task is to extract the moral dimensions present in the question (see definition below). Based on these dimensions, you will generate a set of attentional policies (see definition below). Then, you will generate a short title of the value that is present in the attentional policies. Finally, select the 1-2 moral dimensions that this value applies for most strongly, and generate a summary (see specification below) of those dimensions, describing the situation in which these attentional policies applies with as few words as possible.

The output should be formatted exactly as in the example below.

{moral_dimensions_definition}

{meaningful_choice_definition}

{attentional_policy_definition}

{summary_specification}

=== Example Input ===
# Question
I'm really stressed and overwhelmed. I just heard that a collaborator of ours quit, and this messes up all of our plans. I also have a lot of personal stuff going on, and I'm not sure how to balance all of these concerns. I'm not sure what to do.

=== Example Output ===
# Moral Dimensions
When the user is seeking help balancing personal and professional concerns
When the user is dealing with their plans rapidly being uprooted
When the user is feeling overwhelmed
When the user is unsure what to do
When the user is stressed

# Attentional Policies
FEELINGS OF OVERWHELM that indicate I need to take a step back
OPPORTUNITIES to get an overview of the situation
SENSATIONS OF CLARITY that come from seeing the overall picture
ACTIONS I can take from a newfound sense of clarity

# Title
Gaining Clarity

# Most Important Dimensions
When the user is feeling overwhelmed
When the user is unsure what to do

# Most Important Dimensions Summary
When the user is feeling overwhelmed and unsure what to do"""

    user_prompt = "# Question\n" + question
    response = gpt4(prompt, user_prompt)
    policies = [
        ap.strip()
        for ap in response.split("# Attentional Policies")[1]
        .split("# Title")[0]
        .split("\n")
        if ap.strip()
    ]
    title = response.split("# Title")[1].split("# Most Important Dimensions")[0].strip()
    context = response.split("# Most Important Dimensions Summary")[1].strip()

    return {"title": title, "policies": policies, "context": context}


def generate_upgrade(
    title: str, policies: List[str], context: str
) -> {"title": str, "policies": List[str], "story": str}:
    prompt = f"""
You are given a context and a values card. A values card is an encapsulation of a way of a wise way of living in the situation. It is made up of a few attentional policies (see definition below) - policies about what to pay attention to in situations – as well as a title, summarizing the value. A context is a short string describing the situation in which the value is relevant.

Your task is to generate a wiser version of the value. You will do this in several steps:

1. First, generate a short instruction for how one could act based on the value in the context. This should be written as a story from first-person perspective, and only be one or two sentences long.
2. Then, look at the instruction, context and value. When faced with the context, what other important thing could this person be missing? What would a wiser person do in the same situation?
3. Generate a story about someone who used to live by this value for the context, but now realizes there is a better way to approach the context. See guidelines below for what makes a value wiser than another.
4. For the new way of living depicted in the story, create a set of attentional policies adhering to the guidelines below, and a title.

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
        + "\n".join(policies)
        + "\n\n# Title\n"
        + title
    )
    response = gpt4(prompt, user_prompt)
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

    return {"title": wiser_title, "policies": wiser_policies, "story": story}


def perturb_question(
    title: str, policies: List[str], question: str
) -> {"question": str}:
    prompt = f"""You will be given a values card and a question. A values card is an encapsulation of a way of a wise way of living in the situation. It is made up of a few attentional policies (see definition below) - policies about what to pay attention to in situations – as well as a title, summarizing the value. A question is a short string representing the situation in which the value is relevant.

    Your task is to gnerate a perturbed question, describing a similar situation to the original question, but where the value is no longer relevant. The new question should start with the original question, and then describe additional aspects of the situation that makes the value described in the attentional policies no longer the right one to apply. Before generating the question, write a short explanation about why the value is no longer relevant in the new situation.

    The output should be formatted exactly as in the example below.

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
    # Perturbation Explanation
    In the original question, we don't know what is causing the kid to have difficult times. Knowing this might require a different approach than deep care, as this does not address the root cause of the problem. For example, if the child is having a difficult time due to having become a bully, and consequently, having no friends, deep care might not be the best approach. Instead, it might be wise to inquire why this child has become a bully, and how to help them make amends with the other kids.

    # Perturbed Question
    How can I help my child through difficult times? They are struggling to make friends now after having bullied other kids."""

    user_prompt = (
        "# Question\n"
        + question
        + "\n\n# Attentional Policies\n"
        + "\n".join(policies)
        + "\n\n# Title\n"
        + title
    )

    response = gpt4(prompt, user_prompt, temperature=0.2)
    perturbed_explanation = response.split("# Perturbation Explanation")[1].strip()
    perturbed_question = response.split("# Perturbed Question")[1].strip()

    print(perturbed_explanation)

    return perturbed_question
