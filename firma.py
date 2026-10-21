from decimal import Decimal, InvalidOperation, localcontext
import json
from pathlib import Path


class Manager:
    def __init__(self, plik_danych=None):
        self.actions = {}
        self.saldo = Decimal("0.00")
        self.magazyn = {}
        self.historia = []
        self.grosz = Decimal("0.01")
        self.plik_danych = Path(plik_danych) if plik_danych is not None else Path(__file__).with_name("dane.txt")
        self.dziala = True
        self.komendy = "saldo, sprzedaż, zakup, konto, lista, magazyn, przegląd, koniec"
        self.zarejestruj_komendy()

    def assign(self, name):
        def decorate(callback):
            self.actions[name] = callback
            return callback
        return decorate

    def execute(self, name):
        if name not in self.actions:
            print("Nieznana komenda. Wybierz jedną z dostępnych komend.")
        else:
            return self.actions[name](self)

    def wczytaj_dane(self):
        if not self.plik_danych.exists():
            return
        with open(self.plik_danych, "r", encoding="utf-8") as plik:
            dane = json.load(plik)
        self.saldo = Decimal(dane["saldo"])
        self.magazyn = dane["magazyn"]
        self.historia = dane["historia"]
        for produkt in self.magazyn.values():
            produkt["cena"] = Decimal(produkt["cena"])

    def zapisz_dane(self):
        dane = {"saldo": str(self.saldo), "magazyn": {}, "historia": self.historia}
        for nazwa, produkt in self.magazyn.items():
            dane["magazyn"][nazwa] = {
                "cena": str(produkt["cena"]), "ilosc": produkt["ilosc"]
            }
        plik_tymczasowy = self.plik_danych.with_suffix(".tmp")
        with open(plik_tymczasowy, "w", encoding="utf-8") as plik:
            json.dump(dane, plik, ensure_ascii=False, indent=4)
        plik_tymczasowy.replace(self.plik_danych)

    def wczytaj_kwote(self, komunikat):
        tekst = input(komunikat).strip().replace(',', '.')
        try:
            kwota = Decimal(tekst)
        except InvalidOperation:
            raise ValueError('Podaj poprawną kwotę, np. 125,50.') from None
        if not kwota.is_finite() or abs(kwota) > Decimal('999999999999.99'):
            raise ValueError('Kwota musi być skończona i nie przekraczać 999999999999,99.')
        if kwota != kwota.quantize(self.grosz):
            raise ValueError('Kwota może mieć najwyżej dwa miejsca po przecinku.')
        return kwota.quantize(self.grosz)

    def wczytaj_nazwe(self):
        nazwa = input('Nazwa produktu: ').strip().casefold()
        if not nazwa:
            raise ValueError('Nazwa produktu nie może być pusta.')
        return nazwa

    def wczytaj_ilosc(self):
        try:
            ilosc = int(input('Liczba sztuk: ').strip())
        except ValueError:
            raise ValueError('Liczba sztuk musi być liczbą całkowitą.') from None
        if not 1 <= ilosc <= 1000000000:
            raise ValueError('Liczba sztuk musi być dodatnia i nie większa niż 1000000000.')
        return ilosc

    def pieniadze(self, kwota):
        return f'{kwota:.2f} zł'.replace('.', ',')

    def pokaz_produkt(self, nazwa, produkt):
        print(f"{nazwa}: {produkt['ilosc']} szt., cena jednostkowa: {self.pieniadze(produkt['cena'])}")

    def pokaz_historie(self):
        od = input('Od indeksu (Enter = początek): ').strip()
        do = input('Do indeksu (Enter = koniec, włącznie): ').strip()
        liczba = len(self.historia)
        informacja = f'Liczba zapisanych komend: {liczba}.'
        if liczba:
            informacja += f' Dostępne indeksy: 0–{liczba - 1}.'
        try:
            poczatek = int(od) if od else 0
            koniec = int(do) if do else liczba - 1
        except ValueError:
            print('Indeksy muszą być liczbami całkowitymi. ' + informacja)
            return
        if not liczba and (not od) and (not do):
            print('Historia jest pusta. ' + informacja)
            return
        if not 0 <= poczatek <= koniec < liczba:
            print('Nieprawidłowy zakres. ' + informacja)
            return
        for indeks in range(poczatek, koniec + 1):
            print(f'[{indeks}] {self.historia[indeks]}')

    def transakcja(self, komenda):
        nazwa = self.wczytaj_nazwe()
        cena = self.wczytaj_kwote('Cena jednostkowa: ')
        if cena <= 0:
            raise ValueError('Cena produktu musi być większa od zera.')
        ilosc = self.wczytaj_ilosc()
        wartosc = cena * ilosc
        if komenda == 'zakup':
            if self.saldo < wartosc:
                raise ValueError(f'Brak środków: zakup kosztuje {self.pieniadze(wartosc)}, stan konta wynosi {self.pieniadze(self.saldo)}.')
            poprzednia_ilosc = self.magazyn.get(nazwa, {}).get('ilosc', 0)
            self.magazyn[nazwa] = {'cena': cena, 'ilosc': poprzednia_ilosc + ilosc}
            self.saldo -= wartosc
        else:
            if nazwa not in self.magazyn:
                raise ValueError('Tego produktu nie ma w magazynie.')
            if self.magazyn[nazwa]['ilosc'] < ilosc:
                raise ValueError(f"Za mało sztuk. Dostępne: {self.magazyn[nazwa]['ilosc']}.")
            self.magazyn[nazwa]['ilosc'] -= ilosc
            self.saldo += wartosc
        self.historia.append(f'{komenda}: {nazwa}, {ilosc} szt. po {self.pieniadze(cena)}; wartość: {self.pieniadze(wartosc)}; stan konta: {self.pieniadze(self.saldo)}')
        print(f'Wykonano {komenda}. Stan konta: {self.pieniadze(self.saldo)}')

    def zarejestruj_komendy(self):
        @self.assign("wczytaj")
        def wczytaj_dane(self):
            self.wczytaj_dane()

        @self.assign("zapisz")
        def zapisz_dane(self):
            self.zapisz_dane()

        @self.assign("saldo")
        def saldo(self):
            kwota = self.wczytaj_kwote('Kwota do dodania lub odjęcia (ze znakiem minus): ')
            self.saldo += kwota
            self.historia.append(f'saldo: {self.pieniadze(kwota)}; stan konta: {self.pieniadze(self.saldo)}')
            print(f'Stan konta: {self.pieniadze(self.saldo)}')
            self.execute("zapisz")

        @self.assign("konto")
        def konto(self):
            print(f'Stan konta: {self.pieniadze(self.saldo)}')

        @self.assign("lista")
        def lista(self):
            if not self.magazyn:
                print('Magazyn jest pusty.')
            for nazwa, produkt in sorted(self.magazyn.items()):
                self.pokaz_produkt(nazwa, produkt)

        @self.assign("magazyn")
        def magazyn(self):
            nazwa = self.wczytaj_nazwe()
            if nazwa in self.magazyn:
                self.pokaz_produkt(nazwa, self.magazyn[nazwa])
            else:
                print('Tego produktu nie ma w magazynie.')

        @self.assign("przegląd")
        def przeglad(self):
            self.pokaz_historie()

        @self.assign("zakup")
        def zakup(self):
            self.transakcja("zakup")
            self.execute("zapisz")

        @self.assign("sprzedaż")
        def sprzedaz(self):
            self.transakcja("sprzedaż")
            self.execute("zapisz")

        @self.assign("koniec")
        def koniec(self):
            print("Zakończono program.")
            self.dziala = False

    def uruchom(self):
        with localcontext() as kontekst:
            kontekst.prec = 60
            self.petla()

    def petla(self):
        try:
            self.execute("wczytaj")
            self.execute("zapisz")
        except (OSError, ValueError, KeyError, TypeError, AttributeError, InvalidOperation) as blad:
            print(f"Nie można odczytać lub przygotować pliku danych: {blad}")
            return
        print("Ewidencja firmy. Dane są zapisywane w pliku dane.txt.")
        while self.dziala:
            print(f"\nDostępne komendy: {self.komendy}")
            try:
                komenda = input("Wprowadź komendę: ").strip().casefold()
                komenda = {"sprzedaz": "sprzedaż", "przeglad": "przegląd"}.get(komenda, komenda)
                if komenda in self.komendy.split(", "):
                    self.execute(komenda)
                else:
                    print("Nieznana komenda. Wybierz jedną z dostępnych komend.")
            except OSError as blad:
                print(f"Nie udało się zapisać ostatniej operacji: {blad}")
                print("Program zostanie zakończony. Sprawdź dostęp do pliku dane.txt.")
                break
            except ValueError as blad:
                print(f"Nie wykonano operacji: {blad}")
            except (EOFError, KeyboardInterrupt):
                print("\nPrzerwano program.")
                break


if __name__ == "__main__":
    Manager().uruchom()

