import test from 'node:test';
import assert from 'node:assert/strict';
import {translate} from '../dist/i18n.js';
test('German locale variants translate touch navigation without corrupting app names', () => {
    assert.equal(translate('Overview',['de_DE.UTF-8','de']), 'Übersicht');
    assert.equal(translate('Search apps',['en_US']), 'Search apps');
    assert.equal(translate('Third-party app',['de']), 'Third-party app');
});
