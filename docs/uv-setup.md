# uv Package Manager Setup

This project uses [uv](https://github.com/astral-sh/uv) as the Python package manager for faster dependency resolution and installation.

## Installation

### Linux/macOS
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Windows
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Via pip (alternative)
```bash
pip install uv
```

## Usage

### Create Virtual Environment
```bash
cd backend
uv venv
```

### Activate Virtual Environment
```bash
# Linux/macOS
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\activate

# Windows CMD
.venv\Scripts\activate.bat
```

### Install Dependencies
```bash
# Install project dependencies
uv pip install -e .

# Install with dev dependencies
uv pip install -e ".[dev]"
```

### Add New Package
```bash
# Add to pyproject.toml dependencies, then:
uv pip install <package-name>
```

## Benefits over pip

- **10-100x faster** dependency resolution
- **Disk space efficient** with global cache
- **Drop-in replacement** for pip commands
- **Better error messages** for dependency conflicts
- **Reproducible builds** with lockfile support

## Commands Comparison

| pip | uv |
|-----|-----|
| `pip install -e .` | `uv pip install -e .` |
| `pip install package` | `uv pip install package` |
| `pip freeze > requirements.txt` | `uv pip freeze > requirements.txt` |
| `python -m venv .venv` | `uv venv` |

## Troubleshooting

**Issue: uv command not found**
- Ensure `~/.cargo/bin` (Linux/macOS) or `%USERPROFILE%\.cargo\bin` (Windows) is in PATH
- Restart terminal after installation

**Issue: Permission denied**
- Use `--user` flag: `pip install --user uv`
- Or run with appropriate permissions

**Issue: Slow first install**
- First run downloads packages to global cache (~/.cache/uv/)
- Subsequent installs are much faster
