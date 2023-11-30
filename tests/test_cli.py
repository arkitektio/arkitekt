from click.testing import CliRunner
from arkitekt.cli.main import cli
import os


def test_init(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        result = runner.invoke(cli, "init")
        



        assert result.exit_code == 0

        assert os.path.exists(os.path.join(td, ".arkitekt"))

        assert os.path.exists(os.path.join(td, ".arkitekt", "manifest.yaml"))


        