from openai import OpenAI


def main():
    client = OpenAI(
        base_url="http://localhost:1234/v1",
        api_key="lm-studio",
    )

    models = client.models.list()

    print(
        "=== LM Studio Models ==="
    )

    for model in models.data:
        print(model.id)


if __name__ == "__main__":
    main()