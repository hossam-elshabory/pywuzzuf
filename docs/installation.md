---
icon: material/download
---

# Installation

??? tip "Prerequisites (OS Specific)"

    In most cases, `pip install pywuzzuf` will work out of the box. If you encounter build errors or are on a platform without pre-built wheels, ensure you have a C compiler available.

    === "Windows"

        Install the **Microsoft Visual C++ Build Tools**.

        1. Download the installer from the [Visual Studio website](https://visualstudio.microsoft.com/visual-cpp-build-tools/).
        2. Select **"Desktop development with C++"** in the installer.
        3. Restart your terminal after installation.

    === "macOS"

        Install Xcode Command Line Tools:

        ```bash
        xcode-select --install
        ```

    === "Linux (Debian/Ubuntu)"

        Install GCC and Python development headers:

        ```bash
        sudo apt-get update
        sudo apt-get install build-essential python3-dev
        ```

    === "Linux (Alpine)"

        Alpine Linux uses `musl` instead of `glibc`, which often requires compiling from source.

        ```bash
        apk add gcc musl-dev python3-dev libffi-dev
        ```

## Package Managers

PyWuzzuf supports Python 3.12+. **We recommend using `uv`** for faster dependency resolution and virtual environment management.

=== "uv"

    ```bash
    uv add pywuzzuf
    ```

=== "pip"

    ```bash
    pip install pywuzzuf
    ```

=== "Poetry"

    ```bash
    poetry add pywuzzuf
    ```

## Verifying Installation

Run the following command to verify that the package and its dependencies are correctly installed. This checks the import without making a network request.

```bash
python -c "import pywuzzuf; print(f'PyWuzzuf v{pywuzzuf.__version__} loaded successfully.')"
```

If this prints the version, you are ready to start searching.

## Troubleshooting

### Build Errors: `curl_cffi`

If you see errors related to `curl_cffi` compilation:

1.  **Upgrade pip**: Older pip versions may not find the correct binary wheel.
    ```bash
    pip install --upgrade pip
    ```
2.  **Check Prerequisites**: Ensure the C compiler for your OS (see above) is installed.
3.  **Platform Support**: If you are on an exotic platform (e.g., ARM Linux without wheels), you must compile from source. Refer to the [curl_cffi documentation](https://github.com/yifeikong/curl_cffi) for detailed build requirements.

### `ImportError` on Windows

If you encounter `ImportError: DLL load failed` on Windows, it usually indicates missing Visual C++ Redistributables. Install the [latest supported Visual C++ downloads](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist).
