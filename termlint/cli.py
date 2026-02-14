"""Command-line interface for termlint."""

import click


@click.group()
def termlint_cli():
    """Command-line interface for termlint."""
    pass


@termlint_cli.command()
def install_models():
    """Install required models for all extractors."""
    from termlint.extraction.extractors.rule import DEFAULT_MODEL
    try:
        import spacy
        spacy.load(DEFAULT_MODEL)
        click.echo(f"spaCy model '{DEFAULT_MODEL}' is already installed.")
    except OSError:
        click.echo(f"Installing spaCy model '{DEFAULT_MODEL}'...")
        spacy.load(DEFAULT_MODEL)
        click.echo(f"spaCy model '{DEFAULT_MODEL}' installed successfully.")


@termlint_cli.command()
def main():
    """Main entry point for termlint CLI."""
    click.echo("Welcome to termlint CLI!")
    click.echo("Use 'termlint_cli install-models' to install required models.")


if __name__ == "__main__":
    termlint_cli()
