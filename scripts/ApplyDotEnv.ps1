Get-Content .env | Where-Object {$_ -match '='} | ForEach-Object {
    $name, $value = $_.split('=', 2)
    Set-Content "Env:\$name" $value
}
