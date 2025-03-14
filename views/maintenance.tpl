<b style="color: red;">Warning: Maintenance shutdown at <span id="maintenance">tba</span></b>
<script>
let date = new Date({{timestamp*1000}});
let text = date.toLocaleDateString() + ' at ' + date.toLocaleTimeString();
$('#maintenance')[0].innerHTML = text;
</script>
