import typer

app = typer.Typer()

@app.command()
def add(x: float, y: float):
    """Add two numbers."""
    typer.echo(f"The sum is: {x + y}")

if __name__ == "__main__":
    app()
