function fetch_status() {
    $j.getJSON(program_base_url + 'unenroll_status', function (data) {
        console.log(data);
    });
}

$j(document).ready(fetch_status);
