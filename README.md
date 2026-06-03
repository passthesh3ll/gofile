# Gofile

![image](https://i.postimg.cc/Y2PpsBtf/3.png)

A python Gofile client. You can upload files or entire folders to Gofile, providing a simple command-line interface with progress tracking and optional logging of download links.

## Dependencies

- `requests`
- `requests_toolbelt`
- `tqdm`
- `colorama`

```bash
pip install requests requests-toolbelt tqdm colorama
```

## Example

Upload a file:

```bash
python gofile.py /path/to/file.txt
```

![image](https://i.postimg.cc/6QsFGsNG/image.png)

Upload a folder:

```bash
python gofile.py /path/to/dir/
```

![image](https://i.postimg.cc/SNSSJMGK/image.png)

Parallel upload:

```bash
python gofile.py --parallel 3 /path/to/dir/
```
![image](https://i.postimg.cc/KjMBPPgv/image.png)

## Help

```
usage: gofile.py [-h] [--log] [--wait WAIT] [--proxy [PROXY]] [--parallel PARALLEL] path

upload files or folders to Gofile

positional arguments:
  path                 path to the file or folder to upload

options:
  -h, --help           show this help message and exit
  --log                save upload links to _links.txt file
  --wait WAIT          seconds to wait between uploads (default: 5sec)
  --proxy [PROXY]      use proxy (default if empty: socks5://127.0.0.1:9050, or specify custom proxy URL)
  --parallel PARALLEL  number of parallel uploads (default: 1)
```
