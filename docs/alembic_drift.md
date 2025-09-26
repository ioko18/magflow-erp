# Aliniere versiuni (fără rulare DDL)

## Comanda `alembic stamp`

Comanda `alembic stamp` marchează baza de date ca fiind la o anumită versiune, fără a rula efectiv migrările. Această comandă este utilă în următoarele situații:

1. **Alinierea bazei de date existente**: Când aveți o bază de date care corespunde deja unei versiuni specifice din istoricul de migrări, dar tabela `alembic_version` nu a fost actualizată corespunzător.

1. **Sincronizarea mediilor**: Pentru a sincroniza mediile de dezvoltare, testare sau producție fără a rula din nou migrările care au fost deja aplicate.

1. **Corectarea derapajelor de versiune**: Când există o discrepanță între versiunea înregistrată și starea reală a bazei de date.

## Cum se folosește

```bash
alembic stamp <revision>
```

Unde `<revision>` poate fi:

- Un hash de revizuire specific (ex: `a1b2c3d4`)
- O referință relativă (ex: `head`, `head-1`)
- Un tag specific din fișierele de migrare

## Exemplu practic

```bash
# Marchează baza de date ca fiind la ultima versiune
alembic stamp head

# Marchează o revizuire specifică
alembic stamp a1b2c3d4

# Marchează o versiune anterioară
alembic stamp head-1
```

## Avertizări

- **Verificați întotdeauna** că structura bazei de date corespunde exact cu revizuirea pe care o sămnați. Dacă nu se potrivește, puteți avea probleme de sincronizare.
- Nu folosiți `stamp` pentru a "sări" peste migrări. Dacă o migrare eșuează, remediați cauza, nu marcați pur și simplu baza de date ca fiind actualizată.
- În mediile de producție, utilizați cu precauție și doar dacă sunteți sigur de implicații.

## Verificare

Pentru a verifica starea curentă a bazei de date:

```bash
alembic current
```

Această comandă va afișa versiunea curentă a bazei de date și dacă există migrări în așteptare.
