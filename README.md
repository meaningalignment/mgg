# Moral Graph Generation

Code for generating synthetic moral graphs.

# Setup

### Requirements

* OpenAI API key

### Env Variables

Copy the .env.example file and add values from the .env file in the main project.

### Python Environment

The project currently uses python `3.10.9`. Using other python versions may cause issues.

Make sure you're using the right python version:

`pyenv install 3.10.9`

`pyenv use 3.10.9`

Running `python --version` should return `3.10.9`.

Create a python virtual environment:

`python -m venv .venv`

Activate the environment:

`source .venv/bin/activate`

Install dependencies:

`pip install -r requirements.txt`

### Prisma

In order to query the database through Prisma, run:

`python -m prisma generate`