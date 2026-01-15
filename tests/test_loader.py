"""
Tests for the environment file loader.
"""

import pytest
import pytest_asyncio
import tempfile
from pathlib import Path

from use_env.loader import EnvLoader, EnvVariable, SecretReference, EnvFileError
from use_env.config import UseEnvConfig


class TestEnvLoader:
    """Tests for the EnvLoader class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def env_file(self, temp_dir, secret_file):
        """Create a test environment file."""
        content = f"""# This is a comment
DATABASE_HOST=localhost
DATABASE_PORT=5432
API_KEY=${{env:TEST_API_KEY}}
SECRET=${{file:{secret_file}}}
PLAIN_VALUE=just_a_string
"""
        file_path = temp_dir / ".env.dev"
        file_path.write_text(content)
        return file_path

    @pytest.fixture
    def secret_file(self, temp_dir):
        """Create a test secret file."""
        file_path = temp_dir / "secret.txt"
        file_path.write_text("file_secret_value")
        return file_path

    def test_parse_env_file(self, env_file):
        """Test parsing an environment file."""
        loader = EnvLoader()

        content = env_file.read_text()
        lines = content.splitlines()
        variables = loader._parse_lines(lines)

        assert len(variables) == 5

        # Check first variable (line 4 in file, but line 2 after skipping empty/comment lines)
        assert variables[0].key == "DATABASE_HOST"
        assert variables[0].value == "localhost"
        assert variables[0].line_number == 2  # After skipping 2 header lines

        # Check variable with reference
        api_key = next(v for v in variables if v.key == "API_KEY")
        assert api_key.value == "${env:TEST_API_KEY}"

    def test_find_references(self, env_file, secret_file):
        """Test finding secret references in a file."""
        loader = EnvLoader()

        content = env_file.read_text()
        lines = content.splitlines()
        variables = loader._parse_lines(lines)
        references = loader._find_references(content, variables)

        assert len(references) == 2

        # Check env reference
        env_ref = next(r for r in references if r.provider_name == "env")
        assert env_ref.key == "API_KEY"
        assert env_ref.reference == "TEST_API_KEY"

        # Check file reference (now uses absolute path)
        file_ref = next(r for r in references if r.provider_name == "file")
        assert file_ref.key == "SECRET"
        assert file_ref.reference == str(secret_file)

    def test_parse_with_quoted_values(self, temp_dir):
        """Test parsing quoted values."""
        content = """QUOTED_DOUBLE="value in quotes"
QUOTED_SINGLE='single quoted'
UNQUOTED=no_quotes
"""
        file_path = temp_dir / "quoted.env"
        file_path.write_text(content)

        loader = EnvLoader()
        content = file_path.read_text()
        lines = content.splitlines()
        variables = loader._parse_lines(lines)

        assert variables[0].value == "value in quotes"
        assert variables[1].value == "single quoted"
        assert variables[2].value == "no_quotes"

    def test_parse_with_empty_lines_and_comments(self, temp_dir):
        """Test that empty lines and comments are skipped."""
        content = """# Comment line

# Another comment

KEY=value

# Final comment
"""
        file_path = temp_dir / "comments.env"
        file_path.write_text(content)

        loader = EnvLoader()
        content = file_path.read_text()
        lines = content.splitlines()
        variables = loader._parse_lines(lines)

        assert len(variables) == 1
        assert variables[0].key == "KEY"

    def test_parse_invalid_lines(self, temp_dir):
        """Test that invalid lines (no equals sign) are skipped."""
        content = """VALID_KEY=value
INVALID_LINE_NO_EQUALS
ANOTHER_VALID=value2
"""
        file_path = temp_dir / "invalid.env"
        file_path.write_text(content)

        loader = EnvLoader()
        content = file_path.read_text()
        lines = content.splitlines()
        variables = loader._parse_lines(lines)

        assert len(variables) == 2
        assert variables[0].key == "VALID_KEY"
        assert variables[1].key == "ANOTHER_VALID"

    def test_replace_references(self):
        """Test replacing references in content."""
        loader = EnvLoader()

        content = "KEY1=${env:VAR1}\nKEY2=${file:path.txt}"
        resolved = {
            "env://VAR1": "resolved_value1",
            "file://path.txt": "resolved_value2",
        }

        result = loader._replace_references(content, resolved)

        assert "resolved_value1" in result
        assert "resolved_value2" in result
        assert "${" not in result

    @pytest.mark.asyncio
    async def test_load_file_not_found(self, temp_dir):
        """Test that loading a nonexistent file raises an error."""
        loader = EnvLoader()

        with pytest.raises(EnvFileError) as exc_info:
            await loader.load(temp_dir / "nonexistent.env")

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_load_with_env_provider(self, temp_dir, env_file, secret_file):
        """Test loading a file with env provider."""
        import os

        # Import to register providers
        from use_env.providers.built_in import register_built_in_providers

        register_built_in_providers()

        os.environ["TEST_API_KEY"] = "test_api_key_value"

        try:
            loader = EnvLoader()
            result = await loader.load(str(env_file), str(temp_dir / ".env"))

            assert result.variables_count == 5
            assert result.secrets_resolved == 2  # Both env and file references

            output = result.output_path.read_text()
            assert "test_api_key_value" in output
            assert "${env:TEST_API_KEY}" not in output
            assert "file_secret_value" in output
        finally:
            await loader.close()

    @pytest.mark.asyncio
    async def test_load_with_file_provider(self, temp_dir, env_file, secret_file):
        """Test loading a file with file provider."""
        # Import to register providers
        from use_env.providers.built_in import register_built_in_providers

        register_built_in_providers()

        loader = EnvLoader()
        result = await loader.load(str(env_file), str(temp_dir / ".env"))

        assert result.variables_count == 5
        assert result.secrets_resolved == 2

        output = result.output_path.read_text()
        assert "file_secret_value" in output
        assert "${file:./secret.txt}" not in output

        await loader.close()

    @pytest.mark.asyncio
    async def test_output_path_default(self, temp_dir, env_file, secret_file):
        """Test that default output path is correct."""
        import os

        os.environ["TEST_API_KEY"] = "test_api_key"

        loader = EnvLoader()
        result = await loader.load(str(env_file))

        assert result.output_path == temp_dir / ".env"

        await loader.close()

    @pytest.mark.asyncio
    async def test_custom_output_path(self, temp_dir, env_file, secret_file):
        """Test custom output path."""
        import os

        os.environ["TEST_API_KEY"] = "test_api_key"

        loader = EnvLoader()
        custom_output = temp_dir / "custom_output.env"

        result = await loader.load(str(env_file), str(custom_output))

        assert result.output_path == custom_output
        assert custom_output.exists()

        await loader.close()


class TestEnvVariable:
    """Tests for the EnvVariable dataclass."""

    def test_create_env_variable(self):
        """Test creating an EnvVariable."""
        var = EnvVariable(
            key="TEST",
            value="value",
            line_number=1,
            raw_value="TEST=value",
        )

        assert var.key == "TEST"
        assert var.value == "value"
        assert var.line_number == 1
        assert var.raw_value == "TEST=value"


class TestSecretReference:
    """Tests for the SecretReference dataclass."""

    def test_create_secret_reference(self):
        """Test creating a SecretReference."""
        ref = SecretReference(
            provider_name="env",
            reference="VAR_NAME",
            key="MY_VAR",
            start_pos=0,
            end_pos=20,
        )

        assert ref.provider_name == "env"
        assert ref.reference == "VAR_NAME"
        assert ref.key == "MY_VAR"
        assert ref.start_pos == 0
        assert ref.end_pos == 20
