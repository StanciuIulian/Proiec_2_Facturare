import os
from sqlalchemy import (
    Column,
    Integer,
    String,
    create_engine,
    Float,
    ForeignKey,
    DateTime,
    func,
    Table,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

Base = declarative_base()


def get_database_url():
    # programul poate fi utilizat cu 'mysql' sau 'sqlite'
    db_type = os.getenv("DB_TYPE", "sqlite")
    if db_type == "mysql":
        user = os.getenv("MYSQL_USER", "root")
        password = os.getenv("MYSQL_PASSWORD", "password")
        host = os.getenv("MYSQL_HOST", "localhost")
        port = os.getenv("MYSQL_PORT", "3306")
        database = os.getenv("MYSQL_DATABASE", "db_program_facturare")
        return f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{database}"
    else:
        return "sqlite:///db_program_facturare.db"


interactiune_program = True
engine = create_engine(get_database_url())

factura_produs_table = Table(
    "factura_produs",
    Base.metadata,
    Column("factura_id", Integer, ForeignKey("facturi.id"), primary_key=True),
    Column("produs_id", Integer, ForeignKey("produse.id"), primary_key=True),
)


class Client(Base):
    __tablename__ = "clienti"
    id = Column(Integer, primary_key=True)
    nume_client = Column(String(30), nullable=False)
    cui = Column(String(20), nullable=False)
    adresa_client = Column(String(100), nullable=False)
    facturi_emise = relationship(
        "Factura", back_populates="furnizor", foreign_keys="Factura.furnizor_id"
    )

    def __repr__(self):
        return (
            f"Client(id={self.id}, nume_client={self.nume_client}, cui={self.cui}, "
            f"adresa_client={self.adresa_client})"
        )


class Produs(Base):
    __tablename__ = "produse"
    id = Column(Integer, primary_key=True)
    denumire_produs = Column(String(30), nullable=False)
    cantitate = Column(Integer, nullable=False)
    pret_unitar = Column(Float, nullable=False)
    facturi = relationship(
        "Factura", secondary=factura_produs_table, back_populates="produse"
    )

    def __repr__(self):
        return (
            f"Produs(id={self.id}, denumire_produs={self.denumire_produs}, "
            f"cantitate={self.cantitate}, pret_unitar={self.pret_unitar})"
        )


class Factura(Base):
    __tablename__ = "facturi"
    id = Column(Integer, primary_key=True)
    numar_factura = Column(String(20), unique=True, nullable=False)
    data_emitere = Column(DateTime, default=func.now(), nullable=False)
    furnizor_id = Column(Integer, ForeignKey("clienti.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("clienti.id"), nullable=False)
    furnizor = relationship(
        "Client", back_populates="facturi_emise", foreign_keys=[furnizor_id]
    )
    client = relationship(
        "Client", back_populates="facturi_emise", foreign_keys=[client_id]
    )
    produse = relationship(
        "Produs", secondary=factura_produs_table, back_populates="facturi"
    )

    @property
    def subtotal(self):
        return round(
            sum([produs.pret_unitar * produs.cantitate for produs in self.produse]), 2
        )

    @property
    def total(self):
        tva = 0.19
        return round(self.subtotal * (1 + tva), 2)

    def __repr__(self):
        return (
            f"Factura(id={self.id}, numar_factura={self.numar_factura}, "
            f"data_emitere={self.data_emitere.strftime('%Y-%m-%d')}, "
            f"subtotal={self.subtotal} RON, total={self.total} RON)"
        )


Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()


def adaugare_client(nume_client, cui, adresa_client):
    client = Client(nume_client=nume_client, cui=cui, adresa_client=adresa_client)
    session.add(client)
    session.commit()
    return client


def afisare_client():
    return session.query(Client).all()


def stergere_client(client_id):
    factura_furnizor = session.query(Factura).filter(Factura.furnizor_id == client_id).first()
    if factura_furnizor:
        print(f"Clientul cu id-ul {client_id} nu poate fi sters deoarece este asociat cu factura "
              f"{factura_furnizor.numar_factura}.")
        return
    factura_client = session.query(Factura).filter(Factura.client_id == client_id).first()
    if factura_client:
        print(f"Clientul cu id-ul {client_id} nu poate fi sters deoarece este asociat cu factura "
              f"{factura_client.numar_factura}.")
        return
    client = session.query(Client).filter_by(id=client_id).first()
    if client:
        session.delete(client)
        session.commit()
        print(f"A fost sters din bazade date clientul cu id-ul {client_id}!")
    else:
        print(f"Clientul cu id-ul {client_id}, nu se afla in baza de date!")


def adaugare_produs(denumire_produs, cantitate, pret_unitar):
    produs = Produs(
        denumire_produs=denumire_produs, cantitate=cantitate, pret_unitar=pret_unitar
    )
    session.add(produs)
    session.commit()
    return produs


def afisare_produs():
    return session.query(Produs).all()


def stergere_produs(produs_id):
    factura = session.query(Factura).filter(Factura.produse.any(id=produs_id)).first()
    if factura:
        print(f"Produsul cu id-ul {produs_id} nu poate fi sters deoarece este asociat cu factura "
              f"{factura.numar_factura}.")
        return
    produs = session.query(Produs).filter_by(id=produs_id).first()
    if produs:
        session.delete(produs)
        session.commit()
        print(f"A fost sters din bazade date produsul cu id-ul {produs_id}!")
    else:
        print(f"Produsul cu id-ul {produs_id}, nu se afla in baza de date!")


def generare_numar_factura():
    numar_factura = session.query(func.max(Factura.numar_factura)).scalar()
    if numar_factura is None:
        return "FF0001"
    numar_int = int(numar_factura[2:]) + 1
    return f"FF{numar_int:04d}"


def adaugare_factura(furnizor_id, client_id, produse_ids):
    furnizor = session.query(Client).filter_by(id=furnizor_id).first()
    if not furnizor:
        print(f"Furnizorul cu id-ul {furnizor_id} nu se afla in baza de date!")
        return None

    client = session.query(Client).filter_by(id=client_id).first()
    if not client:
        print(f"Clientul cu id-ul {client_id} nu se afla in baza de date!")
        return None

    produse = session.query(Produs).filter(Produs.id.in_(produse_ids)).all()
    if len(produse) != len(produse_ids):
        produse_baza_date = {produs.id for produs in produse}
        produse_lipsa = set(produse_ids) - produse_baza_date
        print(f"Produsele cu id-ul {', '.join(map(str, produse_lipsa))} nu se afla in baza de date!")
        return None

    numar_factura = generare_numar_factura()
    factura = Factura(
        numar_factura=numar_factura,
        furnizor_id=furnizor_id,
        client_id=client_id,
        produse=produse,
    )
    session.add(factura)
    session.commit()
    print(f"Factura a fost emisa cu succes: {factura}")
    return factura


def stergere_factura(factura_id):
    factura = session.query(Factura).filter_by(id=factura_id).first()
    if factura:
        session.delete(factura)
        session.commit()
        print(f"A fost sters din baza de date factura cu id-ul {factura_id}!")
    else:
        print(f"Factura cu id-ul {factura_id}, nu se afla in baza de date!")


def genereaza_factura_txt(factura_id):
    factura = session.query(Factura).filter_by(id=factura_id).first()
    if not factura:
        print(f"Factura cu ID-ul {factura_id} nu a fost gasita!")
        return

    filename = f"Factura_{factura.numar_factura}.txt"
    width_client = 30
    width_furnizor = 30

    continut_factura = [
        f"{'':>30}Factura #{factura.numar_factura}",
        f"Data facturii: {factura.data_emitere.strftime('%d.%m.%Y')}",
        "",
        f"{'CUMPARATOR':<{width_client}} {'':<{width_furnizor}} "
        f"{'FURNIZOR':<{width_furnizor}}",
        f"{factura.client.nume_client:<{width_client}} {'':<{width_furnizor}} "
        f"{factura.furnizor.nume_client:<{width_furnizor}}",
        f"{factura.client.adresa_client:<{width_client}} {'':<{width_furnizor}} "
        f"{factura.furnizor.adresa_client:<{width_furnizor}}",
        f"Reg. com.: [Nr.Reg.Comertului]{'':<{width_furnizor +1}} Reg. com.: [Nr.Reg.Comertului]",
        f"CIF: {factura.client.cui:<{width_client}} {'':<{width_furnizor - 5}} CIF: {factura.furnizor.cui}",
        "",
        f"{'DENUMIRE':<30} {'CANT.':<5} {'PRET UNITAR':<12} {'TOTAL':<10} {'TVA':<10}",
        "-" * 80,
    ]

    for produs in factura.produse:
        total_produs = produs.pret_unitar * produs.cantitate
        tva_produs = round(total_produs * 0.19, 2)
        continut_factura.append(
            f"{produs.denumire_produs:<30} {produs.cantitate:<5} "
            f"{produs.pret_unitar:<12} {total_produs:<10} {tva_produs:<10}"
        )

    continut_factura += [
        "-" * 80,
        f"{'TOTAL':<30} {round(sum(p.cantitate for p in factura.produse), 2):<5} "
        f"{round(sum(p.pret_unitar for p in factura.produse), 2):<12} "
        f"{factura.subtotal:<10} {round(factura.subtotal * 0.19, 2):<10}",
        "",
        f"Total de plata: {factura.total:>10} RON",
        "",
    ]

    continut_factura_str = "\n".join(continut_factura)

    with open(filename, "w", encoding="utf-8") as f:
        f.write(continut_factura_str)

    print(f"\nFactura generata si salvata în fisierul: {filename}")
    print(continut_factura_str)


def iesire_program():
    interactiune_program = False
    return interactiune_program

culori = {
        1: "\033[94m",  # Albastru pentru Client
        2: "\033[92m",  # Verde pentru Produs
        3: "\033[93m",  # Galben pentru Factura
        0: "\033[91m",  # Roșu pentru Iesire
    }

resetare = "\033[0m"


def afisare_meniu(optiune):
    if optiune == 1:
        print(f"{culori[1]}Meniu Client{resetare}")
    elif optiune == 2:
        print(f"{culori[2]}Meniu Produs{resetare}")
    elif optiune == 3:
        print(f"{culori[3]}Meniu Factura{resetare}")
    elif optiune == 0:
        print(f"{culori[0]}Ieșire din program{resetare}")
        return False

    return True


while interactiune_program:

    optiuni = input(
        f"""
        Introduceti cifra optiunii dorite:
        {culori[1]}1 Client{resetare};
        {culori[2]}2 Produs{resetare};
        {culori[3]}3 Factura{resetare};
        {culori[0]}0 Iesire{resetare}
        
        """
    )

    try:
        optiune_int = int(optiuni)
        interactiune_program = afisare_meniu(optiune_int)
        if interactiune_program:
            if optiune_int == 1:
                meniu_clienti = True

                while meniu_clienti:
                    optiuni_clienti = input(
                        f""""
                        {culori[1]}Introduceti cifra obtiunii din meniul clienti dorite:
                        1 Adaugare Client
                        2 Stergere Client
                        3 Afisare Client
                        0 Iesire meniu clienti{resetare}
                        """
                    )
                    try:
                        optiuni_clienti_int = int(optiuni_clienti)
                        if optiuni_clienti_int == 1:
                            try:
                                print(
                                    "Introduceti datele despre Client astfel: Nume Client, RO00000001, Adresa Client"
                                )
                                date_client = input("Introduceti datele clientului: ")
                                client = [date.strip() for date in date_client.split(",")]
                                adaugare_client(client[0], client[1], client[2])
                            except IndexError:
                                print(
                                    "Nu ai introdus toate datele clientului ca in exemplul de mai sus!"
                                )

                        if optiuni_clienti_int == 2:
                            try:
                                print(session.query(Client).all())
                                client_id = input(
                                    "Introduceti id-ul clientului pe caredoriti sa-l stergeti: "
                                )
                                stergere_client(int(client_id))
                            except ValueError:
                                print("Id-ul introdus nu este valid!")

                        if optiuni_clienti_int == 3:
                            if len(session.query(Client).all()) == 0:
                                print("Nu se afla niciun client in baza de date")
                            else:
                                print(session.query(Client).all())

                        if optiuni_clienti_int == 0:
                            meniu_clienti = False

                    except ValueError:
                        print("Optiunea ta nu se regaseste in meniul clienti!")

            elif optiune_int == 2:
                meniu_produse = True

                while meniu_produse:
                    optiuni_produse = input(
                        f"""
                        {culori[2]}Introduceti cifra optiunii din meniul produse dorite:
                        1 Adaugare Produs
                        2 Stergere Produs
                        3 Afisare Produs
                        0 Iesire meniu produse{resetare}
                        """
                    )
                    try:
                        optiuni_produse_int = int(optiuni_produse)
                        if optiuni_produse_int == 1:
                            try:
                                print(
                                    "Adaugati date despre produs astfel: Nume Produs, Cantitate Produs, Pret Produs"
                                )
                                date_produs = input("Introduceti date despre produs: ")
                                produs = [date.strip() for date in date_produs.split(",")]
                                adaugare_produs(produs[0], produs[1], produs[2])

                            except IndexError:
                                print(
                                    "Nu ai introdus toate datele produsului ca in exemplul de mai sus!"
                                )

                        elif optiuni_produse_int == 2:
                            try:
                                print(session.query(Produs).all())
                                produs_id = input(
                                    "Introduceti id-ul produsului pe caredoriti sa-l stergeti: "
                                )
                                stergere_produs(int(produs_id))
                            except ValueError:
                                print("Id-ul introdus nu este valid!")

                        elif optiuni_produse_int == 3:
                            if len(session.query(Produs).all()) == 0:
                                print("Nu se afla niciun produs in baza de date")
                            else:
                                print(session.query(Produs).all())

                        elif optiuni_produse_int == 0:
                            meniu_produse = False

                    except ValueError:
                        print("Optiunea ta nu se regaseste in meniul produse!")

            elif optiune_int == 3:
                meniu_facturi = True

                while meniu_facturi:
                    optiuni_facturi = input(
                        f"""
                        {culori[3]}Introduceti cifra optiunii din meniul facturti dorite:
                        1 Adaugare Factura
                        2 Stergere Factura
                        3 Afisare Facturi
                        4 Generare Factura
                        0 Iesire meniu facturi{resetare}
                        """
                    )

                    try:
                        optiuni_facturi_int = int(optiuni_facturi)
                        if optiuni_facturi_int == 1:
                            try:

                                if len(session.query(Client).all()) <= 1:
                                    try:
                                        print(
                                            "Introduceti datele despre Client astfel: "
                                            "Nume Client, RO00000001, Adresa Client"
                                        )
                                        date_client = input(
                                            "Introduceti datele clientului: "
                                        )
                                        client = [
                                            date.strip() for date in date_client.split(",")
                                        ]
                                        adaugare_client(client[0], client[1], client[2])
                                    except IndexError:
                                        print(
                                            "Nu ai introdus toate datele clientului ca in exemplul de mai sus!"
                                        )

                                print("Selectați ID-ul furnizorului:")
                                print(session.query(Client).all())
                                furnizor_id = int(input("ID-ul furnizorului: "))

                                print("Selectați ID-ul clientului:")
                                print(session.query(Client).all())
                                client_id = int(input("ID-ul clientului: "))

                                if len(session.query(Produs).all()) == 0:
                                    try:
                                        print(
                                            "Adaugati date despre produs astfel: Nume Produs, Cantitate Produs, Pret Produs"
                                        )
                                        date_produs = input(
                                            "Introduceti date despre produs: "
                                        )
                                        produs = [
                                            date.strip() for date in date_produs.split(",")
                                        ]
                                        adaugare_produs(produs[0], produs[1], produs[2])
                                    except IndexError:
                                        print(
                                            "Nu ai introdus toate datele produsului ca in exemplul de mai sus!"
                                        )

                                print(
                                    "Selectați ID-urile produselor (separate prin virgula):"
                                )
                                print(session.query(Produs).all())
                                produse_ids = [
                                    int(id.strip())
                                    for id in input("ID-urile produselor: ").split(",")
                                ]
                                adaugare_factura(furnizor_id, client_id, produse_ids)

                            except ValueError:
                                print("Datele introduse nu sunt valide!")

                        elif optiuni_facturi_int == 2:
                            try:
                                print(session.query(Factura).all())
                                factura_id = int(
                                    input(
                                        "Introduceți ID-ul facturii pe care doriți să o ștergeți: "
                                    )
                                )
                                stergere_factura(factura_id)

                            except ValueError:
                                print("ID-ul introdus nu este valid!")

                        elif optiuni_facturi_int == 3:
                            if len(session.query(Factura).all()) == 0:
                                print(f"Nu se afla nici o factura in baza de date")
                            else:
                                for factura in session.query(Factura).all():
                                    print(
                                        f"Factura(id={factura.id}, nr factura={factura.numar_factura}, "
                                        f"data_emitere={factura.data_emitere}, "
                                        f"subtotal={factura.subtotal}, total={factura.total}"
                                    )

                        elif optiuni_facturi_int == 4:
                            try:
                                facturi = session.query(Factura).all()
                                facturi_id_list = [factura.id for factura in facturi]
                                for factura in facturi:
                                    print(
                                        f"Factura(id={factura.id}, nr factura={factura.numar_factura}, "
                                        f"data_emitere={factura.data_emitere}, "
                                        f"subtotal={factura.subtotal}, total={factura.total}"
                                    )

                                facturi_id = input(
                                    "Introduceți ID-ul facturii pentru care doriți să o generați: "
                                )
                                if facturi_id.isnumeric():
                                    facturi_id = int(facturi_id)
                                    if facturi_id in facturi_id_list:
                                        genereaza_factura_txt(facturi_id)
                                        factura_selectata = next(
                                            f for f in facturi if f.id == facturi_id
                                        )
                                        print(
                                            f"Factura {factura_selectata.numar_factura} a fost generata cu succes!"
                                        )
                                    else:
                                        print(
                                            "ID-ul {facturi_id} introdus nu corespunde niciunei facturi existente."
                                        )
                                else:
                                    print(
                                        "ID-ul {facturi_id} introdus nu este un număr valid!"
                                    )

                            except Exception as e:
                                print(f"Eroare: {e}")

                        elif optiuni_facturi_int == 0:
                            meniu_facturi = False

                    except ValueError:
                        print("Opțiunea ta nu se regasește in meniul facturi!")

            elif optiune_int == 0:
                interactiune_program = False
    except ValueError:
        print("Optiunea ta nu e o obtiune valida!")
