const german: Record<string,string> = {
    'Search apps':'Apps suchen','No matching apps':'Keine passenden Apps',
    'Home':'Start','Overview':'Übersicht','Back':'Zurück','Settings':'Einstellungen',
    'Add favorite':'Favorit hinzufügen','Remove favorite':'Favorit entfernen',
    'Select for split':'Für Teilung auswählen','Split selected apps':'Ausgewählte Apps teilen',
    'Select two apps for split':'Zwei Apps für die Teilung auswählen',
    'Change split':'Teilung ändern','End split':'Teilung beenden',
    'Automatic mode':'Automatik','Rotation lock':'Drehsperre',
    'Battery status unavailable':'Akkustatus nicht verfügbar','Battery':'Akku',
    'No windows on this display':'Keine Fenster auf diesem Bildschirm',
    'Application':'Anwendung','These apps need more space for this split':'Diese Apps brauchen mehr Platz für die Teilung',
    'Choose two resizable main windows on the internal display':'Zwei anpassbare Hauptfenster auf dem internen Bildschirm auswählen',
    'Move widget up':'Widget nach oben','Move widget down':'Widget nach unten','Hide widget':'Widget ausblenden',
};
export function translate(text: string,languages: string[]): string {
    return languages.some(language => language.toLowerCase().startsWith('de')) ? german[text] ?? text : text;
}
