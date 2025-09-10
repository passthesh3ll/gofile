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
![image](https://i.postimg.cc/Mp5MLzRm/image.png)

Upload a folder:

```bash
python gofile.py /path/to/dir/
```
![image](https://i.postimg.cc/jSrMxCsx/1.png)

## Help

```bash
usage: gofile.py [-h] [--log] path

Upload files or folders to Gofile

positional arguments:
  path        Path to the file or folder to upload

options:
  -h, --help  show this help message and exit
  --log       Save upload links to individual <filename>_links.txt files

```


