#para permitir la entreda al puerto 3000 y 8000 con el firewall activado

New-NetFirewallRule -DisplayName "Dev Next.js" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow -Profile Private
New-NetFirewallRule -DisplayName "Dev Django" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow -Profile Private