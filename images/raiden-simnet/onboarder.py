import hashlib
import json
import os
from datetime import datetime
from getpass import getuser
from pathlib import Path
from uuid import uuid4, getnode

import click
import requests
from eth_keyfile import create_keyfile_json
from eth_utils import to_checksum_address


def make_keystore(output_path: str):
    # password = click.prompt(
    #    'Enter new password for keyfile',
    #    hide_input=True,
    #    confirmation_prompt=True,
    #).encode()
    password="123123123".encode()
    now = datetime.utcnow().replace(microsecond=0)
    target_path = Path(output_path)
    target_path.mkdir(parents=True, exist_ok=True)
    keyfile_file = target_path.joinpath(f'UTC--{now.isoformat().replace(":", "-")}Z--{uuid4()!s}')
    keyfile_content = create_keyfile_json(os.urandom(32), password)
    keyfile_file.write_text(json.dumps(keyfile_content))
    return str(keyfile_file), keyfile_content['address']


@click.command()
@click.option(
    '-o', '--output-path',
    type=click.Path(file_okay=False, dir_okay=True),
    default=Path('keystore'),
    show_default=True,
)
@click.option('--faucet-url', default='https://faucet.workshop.raiden.network')
def main(output_path, faucet_url):
    click.secho('Generating keyfile', fg='yellow')
    keyfile_file_path, address = make_keystore(output_path)
    click.echo(
        click.style('Wrote keyfile to ', fg='blue') +
        click.style(keyfile_file_path, fg='green')
    )
    click.echo(
        click.style('Address: ', fg='blue') +
        click.style(to_checksum_address(address), fg='green')
    )


if __name__ == "__main__":
    main()