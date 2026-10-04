Add-Type -AssemblyName PresentationFramework, PresentationCore, WindowsBase

function New-DemoText($Value, $Size = 16, $Color = '#242832') {
    $t = New-Object Windows.Controls.TextBlock
    $t.Text = $Value; $t.FontSize = $Size; $t.Foreground = $Color
    $t.TextWrapping = 'Wrap'; $t.Margin = '0,4,0,4'
    return $t
}
function New-DemoPanel($Horizontal = $false) {
    $p = New-Object Windows.Controls.StackPanel
    if ($Horizontal) { $p.Orientation = 'Horizontal' }
    return $p
}
function New-DemoCard($Child, $Background = '#FFFFFF', $Padding = 18) {
    $b = New-Object Windows.Controls.Border
    $b.Background = $Background; $b.CornerRadius = 16; $b.Padding = $Padding
    $b.Child = $Child; $b.Margin = 6
    return $b
}
function New-DemoButton($Label, $Action, $Background = '#E8EDF4') {
    $b = New-Object Windows.Controls.Button
    $b.Content = $Label; $b.Tag = $Action; $b.Background = $Background
    $b.Foreground = '#202633'; $b.BorderThickness = 0; $b.Padding = '16,10'
    $b.MinHeight = 44; $b.Margin = 4; $b.FontSize = 15; $b.Cursor = 'Hand'
    $b.Add_Click({ param($sender, $eventArgs) Invoke-DemoAction ([string]$sender.Tag) })
    return $b
}
function Add-DemoAt($Canvas, $Child, $X, $Y, $Width, $Height) {
    $Child.Width = [Math]::Max(1,$Width); $Child.Height = [Math]::Max(1,$Height)
    [Windows.Controls.Canvas]::SetLeft($Child,$X); [Windows.Controls.Canvas]::SetTop($Child,$Y)
    [void]$Canvas.Children.Add($Child)
}
function New-DemoApp($Name, $Compact = $false) {
    $p = New-DemoPanel
    $p.Children.Add((New-DemoText "$Name                                      —  □  ×" 18 $script:Ink)) | Out-Null
    $p.Children.Add((New-DemoText 'Simulierte Anwendung' 12 $script:Muted)) | Out-Null
    if ($Name -eq 'Dateien') {
        foreach ($folder in @('Dokumente','Bilder','Projekte','Downloads')) {
            $p.Children.Add((New-DemoText "▣   $folder" 20 $script:Ink)) | Out-Null
        }
    } elseif ($Name -eq 'Kalender') {
        $p.Children.Add((New-DemoText 'Oktober 2026' 28 $script:Ink)) | Out-Null
        $p.Children.Add((New-DemoText "MO     DI     MI     DO     FR`n 5        6       7        8        9`n12      13     14      15      16" 20 $script:Muted)) | Out-Null
    } elseif ($Name -eq 'Einstellungen') {
        $p.Children.Add((New-DemoText 'Übersicht' 28 $script:Ink)) | Out-Null
        $p.Children.Add((New-DemoText "Profil: $($script:Scene.posture)`nAngefordert: $($script:Demo.Requested)`nAngewendet: $($script:Demo.Applied)" 19 $script:Muted)) | Out-Null
        $p.Children.Add((New-DemoButton 'Tablet-Profil simulieren' 'scene|tablet')) | Out-Null
        $p.Children.Add((New-DemoButton 'Updates ansehen' 'scene|update')) | Out-Null
        $p.Children.Add((New-DemoText 'Hardware · Tablet · Diagnose: in der echten App über native Einstellungsseiten verfügbar.' 16 $script:Muted)) | Out-Null
    } else {
        $p.Children.Add((New-DemoText 'Ideen für unterwegs' 28 $script:Ink)) | Out-Null
        $box = New-Object Windows.Controls.TextBox
        $box.Text = $script:Demo.Note; $box.AcceptsReturn = $true; $box.TextWrapping = 'Wrap'
        $box.FontSize = 19; $box.Foreground = $script:Ink; $box.Background = $script:Surface
        $box.BorderThickness = 0; $box.Padding = 12; $box.MinHeight = 100
        $box.Add_TextChanged({param($sender,$eventArgs) $script:Demo.Note = $sender.Text})
        $p.Children.Add($box) | Out-Null
        if (!$Compact) { $p.Children.Add((New-DemoButton 'Bildschirmtastatur anzeigen' 'keyboard')) | Out-Null }
    }
    $scroll = New-Object Windows.Controls.ScrollViewer
    $scroll.VerticalScrollBarVisibility = 'Auto'; $scroll.Content = $p
    return (New-DemoCard $scroll $script:Surface)
}
function Render-Demo {
    $s = $script:Scene; $d = $script:Demo
    $script:Ink = '#242832'; $script:Muted = '#657182'; $script:Surface = '#FAFBFD'
    if ($d.Dark) { $script:Ink = '#F1F4FA'; $script:Muted = '#B6C1D4'; $script:Surface = '#283347' }
    $screen = $script:Screen; $screen.Children.Clear()
    $w = 1080; $h = 680
    if ($d.Portrait) { $w = 700; $h = 940 }
    if ($s.external) { $w = 1440; $h = 760 }
    $screen.Width = $w; $screen.Height = $h
    $gradient = New-Object Windows.Media.LinearGradientBrush
    $gradient.StartPoint = '0,0'; $gradient.EndPoint = '1,1'
    $gradient.GradientStops.Add((New-Object Windows.Media.GradientStop('#18314A',0)))
    $gradient.GradientStops.Add((New-Object Windows.Media.GradientStop('#397D87',0.55)))
    $gradient.GradientStops.Add((New-Object Windows.Media.GradientStop('#91B4A2',1)))
    $screen.Background = $gradient
    $top = New-DemoCard (New-DemoText 'Aktivitäten                          Sonntag, 4. Oktober · 10:08                          WLAN   82 %' 15 '#FFFFFF') '#152538' 7
    Add-DemoAt $screen $top 0 0 $w 48
    $internalW = $w
    if ($s.external) { $internalW = 830 }
    $desktop = $s.id -in @('laptop','sensor','failure')
    $bottom = 88; if ($desktop) { $bottom = 24 }
    $usable = $h - 60 - $bottom
    if ($d.Keyboard) { $usable -= 225 }
    $view = $d.View
    if ($view -eq 'lock') {
        $p = New-DemoPanel
        $p.Children.Add((New-DemoText '10:08' 82 '#FFFFFF')) | Out-Null
        $p.Children.Add((New-DemoText 'Sonntag, 4. Oktober' 26 '#FFFFFF')) | Out-Null
        $p.Children.Add((New-DemoText 'Sitzung gesperrt · Simulation' 20 '#D5E4E8')) | Out-Null
        $p.Children.Add((New-DemoButton 'Demo entsperren' 'scene|tablet')) | Out-Null
        Add-DemoAt $screen $p 80 155 ($w-160) 330
    } elseif ($view -eq 'home') {
        $p = New-DemoPanel
        $p.Children.Add((New-DemoText 'Dein Arbeitsbereich' 36 $script:Ink)) | Out-Null
        $p.Children.Add((New-DemoText 'Uhr 10:08    ·    Akku 82 %    ·    Tablet-Modus' 18 $script:Muted)) | Out-Null
        $search = New-Object Windows.Controls.TextBox
        $search.FontSize = 20; $search.Padding = 14; $search.Margin = '0,14,0,14'
        $search.ToolTip = 'Apps suchen'; $search.Text = $d.Search
        $grid = New-Object Windows.Controls.WrapPanel
        $script:AppGrid = $grid
        $search.Add_TextChanged({param($sender,$eventArgs) $script:Demo.Search = $sender.Text; Render-DemoApps})
        $p.Children.Add($search) | Out-Null; $p.Children.Add($grid) | Out-Null
        $p.Children.Add((New-DemoText 'Favoriten: Notizen · Dateien · Kalender' 16 $script:Muted)) | Out-Null
        $scroll = New-Object Windows.Controls.ScrollViewer; $scroll.Content = $p
        $scroll.VerticalScrollBarVisibility = 'Auto'
        Add-DemoAt $screen (New-DemoCard $scroll $script:Surface 24) 30 65 ($internalW-60) ($usable-15)
        Render-DemoApps
    } elseif ($view -eq 'overview') {
        $p = New-DemoPanel
        $p.Children.Add((New-DemoText 'Offene Anwendungen' 32 '#FFFFFF')) | Out-Null
        $row = New-Object Windows.Controls.WrapPanel
        foreach ($name in @('Notizen','Dateien','Kalender')) {
            $tile = New-DemoPanel
            $tile.Children.Add((New-DemoText $name 23 $script:Ink)) | Out-Null
            $tile.Children.Add((New-DemoText "Fenstervorschau`n`n────────────`n───────`n─────────" 20 $script:Muted)) | Out-Null
            $tile.Children.Add((New-DemoButton 'App öffnen' "app|$name")) | Out-Null
            $card = New-DemoCard $tile $script:Surface; $card.Width = 275; $card.Height = 260
            $row.Children.Add($card) | Out-Null
        }
        $p.Children.Add($row) | Out-Null
        $p.Children.Add((New-DemoButton 'Notizen + Dateien teilen' 'split')) | Out-Null
        $scroll = New-Object Windows.Controls.ScrollViewer; $scroll.Content = $p
        $scroll.VerticalScrollBarVisibility = 'Auto'
        Add-DemoAt $screen $scroll 30 68 ($internalW-60) ($usable-10)
    } elseif ($view -eq 'split') {
        $fraction = @(0.5, (1.0/3), (2.0/3))[$d.Ratio]
        $a = [Math]::Floor(($internalW-48)*$fraction); $b = $internalW-48-$a
        if ($d.Portrait) { $a = [Math]::Floor(($usable-48)*$fraction); $b = $usable-48-$a }
        if ($d.Portrait) {
            Add-DemoAt $screen (New-DemoApp 'Notizen' $true) 0 55 $internalW $a
            Add-DemoAt $screen (New-DemoButton '↕  Teilung ändern' 'ratio') 0 (55+$a) $internalW 48
            Add-DemoAt $screen (New-DemoApp 'Dateien' $true) 0 (103+$a) $internalW $b
        } else {
            Add-DemoAt $screen (New-DemoApp 'Notizen' $true) 0 55 $a $usable
            Add-DemoAt $screen (New-DemoButton '↔' 'ratio') $a 55 48 $usable
            Add-DemoAt $screen (New-DemoApp 'Dateien' $true) ($a+48) 55 $b $usable
        }
    } elseif ($view -eq 'update') {
        $p = New-DemoPanel
        $p.Children.Add((New-DemoText 'Updates' 34 $script:Ink)) | Out-Null
        $p.Children.Add((New-DemoText $d.Update 23 $script:Ink)) | Out-Null
        $p.Children.Add((New-DemoText 'Demo-Version 0.1.1 · alle Zahlen und Zustände sind simuliert.' 16 $script:Muted)) | Out-Null
        foreach ($entry in @(@('Abmeldung simulieren','logout'),@('Nächste Anmeldung simulieren','login'),@('Aktivierungsfehler simulieren','update-fail'),@('Wiederherstellung simulieren','recover'))) {
            $p.Children.Add((New-DemoButton $entry[0] $entry[1])) | Out-Null
        }
        Add-DemoAt $screen (New-DemoCard $p $script:Surface 25) 35 75 ($internalW-70) ($usable-30)
    } else {
        $x = 0; $y = 55; $aw = $internalW; $ah = $usable
        if ($desktop) { $x = 80; $y = 90; $aw -= 190; $ah -= 95 }
        Add-DemoAt $screen (New-DemoApp $d.App) $x $y $aw $ah
    }
    if ($d.Keyboard -and $view -ne 'lock') {
        $p = New-DemoPanel
        foreach ($line in @('Q   W   E   R   T   Z   U   I   O   P','A   S   D   F   G   H   J   K   L','⇧   Y   X   C   V   B   N   M   ⌫','           Leertaste           ↵')) {
            $p.Children.Add((New-DemoText $line 23 $script:Ink)) | Out-Null
        }
        Add-DemoAt $screen (New-DemoCard $p $script:Surface 14) 10 ($h-$bottom-220) ($internalW-20) 220
    }
    if (!$desktop -and $view -ne 'lock') {
        $dock = New-DemoPanel $true
        foreach ($entry in @(@('⌂  Home','home'),@('▦  Übersicht','overview'),@('Notizen','app|Notizen'),@('Dateien','app|Dateien'))) {
            $dock.Children.Add((New-DemoButton $entry[0] $entry[1])) | Out-Null
        }
        $scroll = New-Object Windows.Controls.ScrollViewer; $scroll.Content = $dock
        $scroll.HorizontalScrollBarVisibility = 'Auto'; $scroll.VerticalScrollBarVisibility = 'Disabled'
        Add-DemoAt $screen (New-DemoCard $scroll '#DDE6EF' 4) 10 ($h-82) ($internalW-20) 76
    }
    if ($s.external) {
        Add-DemoAt $screen (New-DemoCard (New-DemoText "Externer Monitor`n`nDesktop bleibt erhalten.`nKeine Tablet-Flächen." 24) '#EDF0F4') 860 100 540 520
    }
    if ($s.id -in @('sensor','failure','minimum')) {
        Add-DemoAt $screen (New-DemoCard (New-DemoText $s.applied 19 '#7A3E06') '#FFF0CB' 12) 30 ($h-95) ($internalW-60) 65
    }
    $script:Description.Text = $s.note
    $script:Status.Text = "SIMULATION    Sensor: $($s.posture)    |    Angefordert: $($d.Requested)    |    Angewendet: $($d.Applied)"
    $script:Geometry.Text = "$(if($d.Portrait){'Hochformat'}else{'Querformat'}) · $(@('50 / 50','1/3 – 2/3','2/3 – 1/3')[$d.Ratio])"
}
function Render-DemoApps {
    $script:AppGrid.Children.Clear()
    foreach ($name in @('Notizen','Dateien','Kalender','Einstellungen')) {
        if ($name -like "*$($script:Demo.Search)*") {
            $button = New-DemoButton "▣`n$name" "app|$name"
            $button.Width = 155; $button.Height = 105
            $script:AppGrid.Children.Add($button) | Out-Null
        }
    }
}
