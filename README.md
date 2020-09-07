# Reindexer Integration Extension

This extension allows to integrate Foliant-managed documentation projects with the in-memory DBMS [Reindexer](https://github.com/Restream/reindexer/) to use it as a fulltext search engine.

The main part of this extension is a preprocessor that prepares data for a search index. In addition, the preprocessor performs basic manipulations with the database and the namespace in it.

Also this extension provides a simple working example of a client-side Web application that may be used to perform searching. By editing HTML, CSS and JS code you may customize it according to your needs.

## Installation

To install the preprocessor, run the command:

```bash
$ pip install foliantcontrib.reindexer
```

To use an example of a client-side Web application for searching, download [these HTML, CSS, and JS files](https://github.com/foliant-docs/foliantcontrib.reindexer/tree/master/webapp_example/) and open the file `index.html` in your Web browser.

## Config

To enable the preprocessor, add `reindexer` to `preprocessors` section in the project config:

```yaml
preprocessors:
    - reindexer
```

The preprocessor has a number of options with the following default values:

```yaml
preprocessors:
    - reindexer:
        reindexer_url: http://127.0.0.1:9088/
        insert_max_bytes: 0
        database: ''
        namespace: ''
        namespace_renamed: ''
        fulltext_config: {}
        actions:
            - drop_database
            - create_database
            - create_namespace
            - insert_items
        use_chapters: true
        format: plaintext
        escape_html: true
        url_transform:
            - '\/?index\.md$': '/'
            - '\.md$': '/'
            - '^([^\/]+)': '/\g<1>'
        require_env: false
        targets: []
```

`reindexer_url`
:   URL of your Reindexer instance. “Root” server URL should be used here, do not add any endpoints such as `/api/v1/db` to it.

`insert_max_bytes`
:   Reindexer itself or a proxy server may limit the available size of request body. Use this option, if it’s needed to split a large amount of content for indexing into several chunks, so each of them will be sent in a separate request. The value of this option represents maximum size of HTTP POST request body in bytes. Allowed values are positive integers starting from `1024`, and `0` (default) meaning no limits.

`database`
:   Name of the database that is used to store your search index.

`namespace`
:   Name of the namespace in the specified database. Namespace in Reindexer means the same as table in relational databases. To store the search index for one documentation project, single namespace is enough.

`namespace_renamed`
:   New namespace name to be applied if the `rename` option is used; see below.

`fulltext_config`
:   The value of the `config` field that refers to the description of the composite fulltext index over the `title` and `content` data fields. Used data structure is described below. [Fulltext indexes config options](https://github.com/Restream/reindexer/blob/master/cpp_src/server/contrib/server.md#fulltextconfig) are listed in the Reindexer’s official documentation.

`actions`
:   Sequence of actions that the preprocessor should to perform. Available item values are:

    * `drop_database`—fully remove the database that is specified as the value of the `database` option. Please be careful using this action when the single database is used to store multiple namespaces. Since this action is included to the default actions list, it’s recommended to use separate databases for each search index. The default list of actions assumes that in most cases it’s needed to remove and then fully rebuild the index, and wherein the database and the namespace may not exist;
    * `create_database`—create the new database with the name specified as the `database` option value;
    * `drop_namespace`—delete the namespace that is specified as the `namespace` option value. All `*_namespace` actions are applied to the existing database with the name from the `database` option;
    * `truncate_namespace`—remove all items from the namespace that is specified as the `namespace` option value, but keep the namespace itself;
    * `rename_namespace`—rename the existing namespace that has the name specified as the `namespace` option value, to the new name from the `renamed_namespace` option. This action may be useful when a common search index is created for multiple Foliant projects, and the index may remain incomplete for a long time during their building;
    * `create_namespace`—create the new namespace with the name from the `namespace` option;
    * `insert_items`—fill the namespace that is specified in the `namespace` option, with the content that should be indexed. Each data item added to the namespace corresponds a single Markdown file of the documentation project.

`use_chapters`
:   If set to `true` (by default), the preprocessor applies only to the files that are mentioned in the `chapters` section of the project config. Otherwise, the preprocessor applies to all Markdown files of the project.

`format`
:   Format that the source Markdown content should be converted to before adding to the index; available values are: `plaintext` (by default), `html`, `markdown` (for no conversion).

`escape_html`
:   If set to `true` (by default), HTML syntax constructions in the content converted to `plaintext` will be escaped by replacing `&` with `&amp;`, `<` with `&lt;`, `>` with `&gt;`, and `"` with `&quot;`.

`url_transform`
:   Sequence of rules to transform local paths of source Markdown files into URLs of target pages. Each rule should be a dictionary. Its data is passed to the [`re.sub()` method](https://docs.python.org/3/library/re.html#re.sub): key as the `pattern` argument, and value as the `repl` argument. The local path (possibly previously transformed) to the source Markdown file relative to the temporary working directory is passed as the `string` argument. The default value of the `url_transform` option is designed to be used to build static websites with MkDocs backend.

`require_env`
:   If set to `true`, the `FOLIANT_REINDEXER` environment variable must be set to allow the preprocessor to perform any operations with the database and the namespace managed by Reindexer. This flag may be useful in CI/CD jobs.

`targets`
:   Allowed targets for the preprocessor. If not specified (by default), the preprocessor applies to all targets.

## Usage

The preprocessor reads each source Markdown file and prepares three fields for indexing:

* `url`—target page URL. This field is used as the primary key, so it must be unique;
* `title`—document title, it’s taken from the first heading of source Markdown content;
* `content`—source Markdown content, optionally converted into plain text or HTML.

When all the files are processed, the preprocessor calls Reindexer API to insert data items (each item corresponds a single Markdown file) into the specified namespace.

Also the preprocessor may call Reindexer API to manipulate the database or namespace, e.g. to delete previously created search index.

You may perform custom search requests to Reindexer API.

The [simple client-side Web application example](https://github.com/foliant-docs/foliantcontrib.reindexer/tree/master/webapp_example/) that is provided as a part of this extension, sends to Reindexer queries like this:

```json
{
    "namespace": "testing",
    "filters": [
        {
            "field": "indexed_content",
            "cond": "EQ",
            "value": "@title^3 foliant"
        }
    ],
    "select_functions": [
        "content = snippet(<em>,</em>,100,100,'\n\n')"
    ],
    "limit": 50
}

```

To learn how to write efficient queries to Reindexer, you may need to refer to its official documentation on topics: [general use](https://github.com/Restream/reindexer/blob/master/readme.md), [fulltext search](https://github.com/Restream/reindexer/blob/master/fulltext.md), [HTTP REST API](https://github.com/Restream/reindexer/blob/master/cpp_src/server/contrib/server.md).

In the example above, the `indexed_content` field corresponds to the composite index over two fields: `title` and `content` (this index is generated when the namespace is created by the request from the preprocessor). [Text of the search query](https://github.com/Restream/reindexer/blob/master/fulltext.md#text-query-format) starts with `@title^3,content^1` that means that the `title` field of the composite index has triple priority (i.e. weighting factor of 3), and the `content` field has normal priority (i.e. weight coefficient equals to 1). Also the example uses the `snippet()` [select function](https://github.com/Restream/reindexer/blob/master/fulltext.md#using-select-fucntions) to highlight the text that matches the query and to cut off excess.

If you use self-hosted instance of Reindexer, you may need to configure a proxy to append [CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS) headers to HTTP API responses.
