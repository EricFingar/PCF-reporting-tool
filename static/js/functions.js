function delete_prompt(func, message) {
    if (confirm(message))
        return true;
    return false;
}

function view_results(path){
    //network
    var network = document.getElementById("network_elem_hidden").value;

    //port
    var port = document.getElementById("port_elem_hidden").value;

    //ip_hostname
    var ip_hostname = encodeURIComponent(document.getElementById("ip_hostname").value);

    //service
    var service = encodeURIComponent(document.getElementById("service_elem").value);

    //issue
    var issue_name = encodeURIComponent(document.getElementById("issue_name").value);

    //comment
    var comment = encodeURIComponent(document.getElementById("comment_elem").value);

    var checked_str = '';
    if (document.getElementById('high_elem').checked){
        checked_str += '&threats[]=high';
    }
    if (document.getElementById('medium_elem').checked){
        checked_str += '&threats[]=medium';
    }
    if (document.getElementById('low_elem').checked){
        checked_str += '&threats[]=low';
    }
    if (document.getElementById('info_elem').checked){
        checked_str += '&threats[]=info';
    }
    if (document.getElementById('check_elem').checked){
        checked_str += '&threats[]=check';
    }
    if (document.getElementById('checked_elem').checked){
        checked_str += '&threats[]=checked';
    }

    let url = path + '?network='+network+'&port='+port+'&ip_hostname='+ip_hostname+'&service='+service+'&issue_name='+issue_name+'&comment='+comment+checked_str;
    let win = window.open(url, '_blank');
    win.focus();

}

function trimChar(string, charToRemove) {
    while(string.charAt(0)==charToRemove) {
        string = string.substring(1);
    }

    while(string.charAt(string.length-1)==charToRemove) {
        string = string.substring(0,string.length-1);
    }

    return string;
}

