# cupertino-hackathon

Many disabled people are not given the resources to create workouts that benefit them, but using AI, we make workouts specifically for them.

## setup

make a keys.json and in it make 2 values
1. mongodb key
2. openai key

### mongo db
{
    ...
    "mongodb": "connection-to-cluster"
}

when you connect your mongodb make a database called cupertino, then a cluster named user_data

### openai
{
    "openai": "openai-key"
    ...
}

no additional setup

## running

flask --app app.py run --debug