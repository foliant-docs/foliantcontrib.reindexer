function performSearch(textToSearch) {
    // Specify your Reindexer instance API URL for search queries here
    const searchUrl = 'http://localhost:9088/api/v1/db/my_docs/query';

    // Specify the namespace to perform search; note that the database name should be specified in the URL above
    const namespaceName = 'production';

    // Specify your site URL without trailing slash here
    const baseUrl = 'http://localhost';

    // Edit this query if needed. In this simple script, single API request is used for searching, and 50 first search results are shown. You may use AJAX to load more results dynamically

    let query = {
        "namespace": namespaceName,
        "filters": [
            {
                "field": "indexed_content",
                "cond": "EQ",
                "value": "@title^3,content^1 " + textToSearch
            }
        ],
        "select_functions": [
            "content = snippet(<em>,</em>,100,100,'\n\n')"
        ],
        "limit": 50
    };

    let searchRequest = new XMLHttpRequest();

    searchRequest.open('POST', searchUrl, true);
    searchRequest.setRequestHeader('Content-Type', 'application/json; charset=utf-8');

    searchRequest.onload = function() {
        let response = JSON.parse(searchRequest.responseText);

        document.getElementById('foliant_reindexer_total').innerHTML = '<p class="foliant_reindexer_success">Results: ' + response.items.length + '</p>';

        let output = '';

        for(let i = 0; i < response.items.length; i++) {
            output += '<h2>' + response.items[i].title + '</h2><p>Page URL: <a href="' + baseUrl + response.items[i].url + '">' + baseUrl + response.items[i].url + '</a></p><pre>' + response.items[i].content + '</pre>';
        }

        document.getElementById('foliant_reindexer_results').innerHTML = output;
    };

    searchRequest.onerror = function() {
        document.getElementById('foliant_reindexer_total').innerHTML = '<p class="foliant_reindexer_error">Error</p>';
    };

    searchRequest.send(JSON.stringify(query));
}
