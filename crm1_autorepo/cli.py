import click
import crm1


@click.group()
def cli():
    pass


@cli.command()
@click.option("--repo", default="crm1", help="Repository name")
def generate(repo):
    print(f"Generating repository {repo}")
