param([string]$SnapshotDirectory)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot/ui.ps1"
$script:Scenes = Get-Content "$PSScriptRoot/scenarios.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$script:Demo = @{Dark=$false; Portrait=$false; Keyboard=$false; Ratio=0; View='app'; App='Notizen'; Search=''; Note="Eine Idee festhalten.`n`nDieser Text bleibt beim Wechsel der Demo-Szenarien erhalten."; Update='Update vorbereitet · wartet auf Abmeldung'}
function Set-DemoScene($Id) {
    $script:Scene = $script:Scenes | Where-Object id -eq $Id | Select-Object -First 1
    if (!$script:Scene) { throw "Unknown demo scenario: $Id" }
    $script:Demo.View = $script:Scene.view; $script:Demo.Portrait = [bool]$script:Scene.portrait
    $script:Demo.Keyboard = [bool]$script:Scene.keyboard
    $script:Demo.Update = 'Update vorbereitet · wartet auf Abmeldung'
    $script:Demo.Requested = $script:Scene.requested; $script:Demo.Applied = $script:Scene.applied
    $index = [array]::IndexOf(@($script:Scenes.id),$Id)
    if ($script:ScenarioList.SelectedIndex -ne $index) { $script:ScenarioList.SelectedIndex = $index }
    Render-Demo
}
function Invoke-DemoAction($Action) {
    if ($Action.StartsWith('scene|')) { Set-DemoScene ($Action.Split('|')[1]); return }
    if ($Action.StartsWith('app|')) { $script:Demo.App = $Action.Split('|')[1]; $script:Demo.View = 'app' }
    switch ($Action) {
        'home' { $script:Demo.View = 'home'; $script:Demo.Keyboard = $false }
        'overview' { $script:Demo.View = 'overview'; $script:Demo.Keyboard = $false }
        'split' { $script:Demo.View = 'split'; $script:Demo.Keyboard = $false }
        'ratio' { $script:Demo.Ratio = ($script:Demo.Ratio+1)%3 }
        'rotate' { $script:Demo.Portrait = !$script:Demo.Portrait }
        'dark' { $script:Demo.Dark = !$script:Demo.Dark }
        'keyboard' { $script:Demo.Keyboard = !$script:Demo.Keyboard }
        'logout' { $script:Demo.Update = 'Keine grafische Sitzung · Aktivierung simuliert'; $script:Demo.Applied = 'Demo-Update aktiviert' }
        'login' { $script:Demo.Update = 'Nächste Anmeldung · Demo-Version geladen'; $script:Demo.Applied = 'Neue Demo-Version geladen' }
        'update-fail' { $script:Demo.Update = 'Aktivierung fehlgeschlagen · Wiederherstellung erforderlich'; $script:Demo.Applied = 'Aktivierung fehlgeschlagen' }
        'recover' { $script:Demo.Update = 'Vorherige Version wiederhergestellt · simuliert'; $script:Demo.Requested = 'Wiederherstellen'; $script:Demo.Applied = 'Vorherige Demo-Version' }
        'reset' { $script:Demo.Ratio = 0; $script:Demo.Dark = $false; Set-DemoScene 'laptop'; return }
    }
    Render-Demo
}
[xml]$xaml = @'
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" Title="convertibled · Interaktive Szenario-Demo" Width="1400" Height="900" MinWidth="940" MinHeight="680" WindowStartupLocation="CenterScreen" Background="#F3F5F8" FontFamily="Segoe UI">
 <Grid Margin="24">
  <Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="*"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
  <StackPanel Grid.Row="0" Margin="0,0,0,18">
   <TextBlock Text="convertibled" FontSize="32" FontWeight="SemiBold" Foreground="#163948"/>
   <TextBlock Text="Interaktive Windows-Vorschau · angenäherte Darstellung · keine echte GNOME-Sitzung" FontSize="15" Foreground="#536473" Margin="0,5,0,0"/>
  </StackPanel>
  <Grid Grid.Row="1">
   <Grid.ColumnDefinitions><ColumnDefinition Width="250"/><ColumnDefinition Width="*"/></Grid.ColumnDefinitions>
   <DockPanel Grid.Column="0" Margin="0,0,20,0">
    <TextBlock DockPanel.Dock="Top" Text="SZENARIEN" Foreground="#536473" FontWeight="SemiBold" Margin="10,0,0,12"/>
    <ListBox Name="ScenarioList" BorderThickness="0" Background="#E7EDF2" FontSize="16" ScrollViewer.VerticalScrollBarVisibility="Auto"/>
   </DockPanel>
   <Grid Grid.Column="1">
    <Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="*"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
    <WrapPanel Name="Toolbar" Margin="0,0,0,10"/>
    <Border Grid.Row="1" Background="#172433" CornerRadius="18" Padding="12">
     <Viewbox Stretch="Uniform"><Canvas Name="Screen" Width="1080" Height="680" ClipToBounds="True"/></Viewbox>
    </Border>
    <StackPanel Grid.Row="2" Margin="0,12,0,0">
     <TextBlock Name="Geometry" Foreground="#277687" FontWeight="SemiBold" FontSize="15"/>
     <TextBlock Name="Description" FontSize="16" TextWrapping="Wrap" Margin="0,6,0,0" Foreground="#334353"/>
    </StackPanel>
   </Grid>
  </Grid>
  <Border Grid.Row="2" Background="#DEE8EE" CornerRadius="8" Padding="12" Margin="0,18,0,0">
   <TextBlock Name="Status" TextWrapping="Wrap" FontSize="13" Foreground="#244454"/>
  </Border>
 </Grid>
</Window>
'@
$reader = New-Object Xml.XmlNodeReader $xaml
$script:Window = [Windows.Markup.XamlReader]::Load($reader)
foreach ($name in @('Screen','Description','Status','Geometry','Toolbar','ScenarioList')) { Set-Variable -Scope Script -Name $name -Value $script:Window.FindName($name) }
foreach ($scene in $script:Scenes) {
    $item = New-Object Windows.Controls.ListBoxItem; $item.Content = $scene.title; $item.Tag = $scene.id
    $item.Padding = '10,13'; [void]$script:ScenarioList.Items.Add($item)
}
$script:ScenarioList.Add_SelectionChanged({if($script:ScenarioList.SelectedItem){Set-DemoScene $script:ScenarioList.SelectedItem.Tag}})
foreach ($entry in @(@('Drehen','rotate'),@('Hell / Dunkel','dark'),@('Teilung ändern','ratio'),@('Manuell Tablet','scene|tablet'),@('Zurücksetzen','reset'))) {
    [void]$script:Toolbar.Children.Add((New-DemoButton $entry[0] $entry[1]))
}
$script:ScenarioList.SelectedIndex = 0
if ($SnapshotDirectory) {
    $directory = [IO.Path]::GetFullPath($SnapshotDirectory)
    [void][IO.Directory]::CreateDirectory($directory)
    $script:Window.Show()
    foreach ($scene in $script:Scenes) {
        Set-DemoScene $scene.id
        $script:Window.UpdateLayout()
        $root = $script:Window
        $image = New-Object Windows.Media.Imaging.RenderTargetBitmap([int]$root.ActualWidth,[int]$root.ActualHeight,96,96,[Windows.Media.PixelFormats]::Pbgra32)
        $image.Render($root)
        $encoder = New-Object Windows.Media.Imaging.PngBitmapEncoder
        $encoder.Frames.Add([Windows.Media.Imaging.BitmapFrame]::Create($image))
        $file = [IO.File]::Create((Join-Path $directory "$($scene.id).png"))
        try {$encoder.Save($file)} finally {$file.Dispose()}
    }
    Invoke-DemoAction 'scene|home'; Invoke-DemoAction 'dark'; Invoke-DemoAction 'app|Dateien'
    Invoke-DemoAction 'scene|update'; Invoke-DemoAction 'logout'; Invoke-DemoAction 'login'; Invoke-DemoAction 'update-fail'; Invoke-DemoAction 'recover'
    if ($script:Demo.Update -notlike '*wiederhergestellt*') {throw 'Demo action transition failed'}
    $script:Window.Close()
    Write-Output "Rendered $($script:Scenes.Count) scenarios; demo action transitions passed."
} else {
    $script:Window.Width = [Math]::Min(1400,[Windows.SystemParameters]::WorkArea.Width-40)
    $script:Window.Height = [Math]::Min(900,[Windows.SystemParameters]::WorkArea.Height-40)
    [void]$script:Window.ShowDialog()
}
