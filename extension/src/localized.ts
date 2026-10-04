import GLib from 'gi://GLib';
import {translate} from './i18n.js';
export const _ = (text: string): string => translate(text,GLib.get_language_names());
