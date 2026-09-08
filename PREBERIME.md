# ESP32-S3 AirMouse - Poročilo

**Avtorja:** Laris Pintar, Mai Rupnik

---

## 1. Uvod

Projekt temelji na IMU senzorju LSM6DSOX, katerega glavna naloga je posredovanje aktualnih podatkov 3-osnega pospeškomera in 3-osnega žiroskopa na ESP32-S3 preko I2C, ki zapakira podatke v paket in ga preko UDP pošlje na računalnik, kjer se v python klientu zgodijo vse »težje« komputacije (filtri, premiki kazalca, itd.). Vse to skupaj se poveže v našo uporabi »air-mouse« napravo, ki brezžično upravlja kazalec z rotacijo in premikanjem roke.

---

## 2. Komponente

- ESP32-S3 razvojna plošča
- 6-osni IMU LSM6DSOX
- 4x Gumb (»sklopka«, levi klik, desni klik, geste)
- 5X LED diode
- RGB-LED dioda
- Analogni potenciometer, za nastavljanje občutljivosti premikov

---

## 3. Sestava

Vezje je priklopljeno po shemi v tabeli:

| Komponenta | Pin / funkcija | GPIO ESP32-S3 |
| :--- | :--- | :--- |
| LSM6DSOX | SDA | GPIO 21 |
| LSM6DSOX | SCL | GPIO 20 |
| LSM6DSOX | INT (data-ready) | GPIO 7 |
| Gumb sklopka | pull-up vhod | GPIO 1 |
| Levi klik | pull-up vhod | GPIO 35 |
| Desni klik | pull-up vhod | GPIO 16 |
| Gumb za gesto | pull-up vhod | GPIO 3 |
| Potenciometer | ADC1 | GPIO 2 |
| LED levi/desni klik | izhod | GPIO 14 / 11 |
| LED pan / zaklep osi | izhod | GPIO 40 / 13 |
| Overload LED | izhod | GPIO 17 |
| RGB LED (R/G/B) | izhod | GPIO 6 / 5 / 4 |

Na ESP32 so povezani vsi moduli (gumbi, LED diode, IMU, ...). Sama naprava je povezana na breadboard-u, za napajanje pa poskrbi prenosna baterija.

![Sestava naprave na breadboard-u](img/breadboard.jpg)

---

## 4. Opis delovanja

Naprava je razdeljena na dva dela: ESP32-S3 skrbi za zajem podatkov in prenos, Python program na odjemalcu pa za obdelavo in premikanje kazalca.

### 4.1 Zajem in prenos podatkov (ESP32-S3)

LSM6DSOX vzorči žiroskop in pospeškomer s frekvenco 208 Hz. Ob vsakem novem vzorcu senzor na pin INT1 pošlje kratek pulz, na katerega se ESP32-S3 odzove z enim samim branjem vseh 12 bajtov podatkov prek I²C (3 osi žiroskopa in 3 osi pospeškomerja, po 2 bajta na os).

![Branje podatkov senzorja](img/code_read_sensors.png)

Za nastavljanje občutljivosti miške skrbi analogni potenciometer, ki ga ESP32-S3 prek ADC vhoda odčita vsakih 50 ms in njegovo vrednost prenaša v vsakem UDP paketu. S tem uporabnik občutljivost prilagaja med samim delom, brez ponovnega zagona ali nastavljanja programske opreme.

![Branje potenciometra](img/code_potentiometer.png)

Ker so podatki prebrani v enem prenosu, sta oba vzorca časovno usklajena. Program hkrati odšteje odstope žiroskopa, priredi stanja gumbov (4-bitna maska: sklopka, levi klik, desni klik, gesta) in vrednost potenciometra, vse skupaj zapakira v 17-bajtni UDP paket, ter ga pošlje prek Wi-Fi na računalnik.

![Pakiranje UDP paketa](img/code_encode_raw_packet.png)

Vsa Firmware je napisan v jeziku Toit, visokonivojskem jeziku za mikrokrmilnike ESP32. Njegova največja prednost za to nalogo je vgrajena sočasnost, ki poskrbi, da vsak del sistema (vzorčenje IMU, odčitavanje gumbov, potenciometer, Wi-Fi strežnik) teče v svojem »opravilu« brez ročnega upravljanja s prekinitvami ali nitmi. Jezik ima samodejno upravljanje pomnilnika in izjem, kar poenostavi zanesljivo delovanje, če na primer I2C branje ali Wi-Fi povezava odpovesta, napako ujamemo in povezavo ponovno vzpostavimo brez ponovnega zagona naprave. Visokonivosjkost jezika Toit nam tako omogoča hitre iteracije prototipov z novimi funcionalnostmi.

### 4.3 Obdelava podatkov (Python na računalniku)

Program prejme UDP pakete in v treh korakih izračuna premik kazalca:

1. **Kalibracija in mrtva cona:** ko roka miruje, program sproti prilagaja začetno vrednost žiroskopa, da se napaka zaradi odnašanja(»Gyroscope Drift«) ne kopiči. Drobne tresljaje, ki so pod nastavljeno mejo se ignorira, zato da kazalec na zaslonu pri mirovanju ne »pleše«
2. **Filtriranje:** vsako os žiroskopa obdeluje 1-Euro filter: pri počasnem gibanju močno zgladi tresenje, pri hitrih premikih pa se samodejno prilagodi in odpre, da ne povzroča zamika. Hkrati Madgwickov filter združi podatke žiroskopa in pospeškometra ter izračuna naklon roke, ki nam pomaga, da tudi če držimo napravo nekoliko postrani, bo delovala kot, da bi bila ševedno obrnjena pravilno.
3. **Preslikava v piksle:** kotno hitrost pomnoži z občutljivostjo, ki jo sproti nastavljaš s potenciometrom in jo pretvori v relativni premik kazalca. Vsi teji podatki so nato predstavljeni kot premikanje miške po zaslonu.

### 4.4 Načini delovanja

| Način | Kako ga vklopim | Kaj se zgodi |
| :--- | :--- | :--- |
| premikanje kazalca | privzeto | 1-Euro filter + pospeševalna krivulja pri hitrih potezah |
| repozicioniranje /rekalibriranje | držim sklopko | kazalec se zelo upočasni in se skoraj ne premika, roko lahko prestavim nazaj na kurzor |
| klik(levi/desni) | klik levega ali desnega gumba | zgodi se levi ali desni klik |
| dvojni klik | držim gumb geste + levi klik | zgodi se dvojni levi klik |
| sredinski gumb | držim gumb geste + desni klik | zgodi se sredinski klik |
| pomik po vsebini | držim sklopko + naprava v mirovanju za 100ms | vključi se način pomika po vsebini (vertikalno/horizontalno) |
| nazaj | držim gumb geste + sunek v levo | zgodi se OS dogodek "nazaj" |
| naprej | držim gumb geste + sunek v desno | zgodi se OS dogodek "naprej" |

![Terminal na odjemalčevi strani](img/terminal_monitor.png)

Slika prikazuje terminal na odjemalčevi strain, ki prikazuje use aktualne informacije o napravi.

### 4.5 Indikacija stanja z LED diodami

Naprava ima sedem LED diod, ki uporabniku sproti sporočajo stanje sistema. Dve se prižgeta ob držanju levega oziroma desnega klika, rumena pa sveti, kadar obdelava podatkov na mikroprocesorju preseže časovni proračun (več kot 2,4 ms na vzorec), kar pomeni preobremenitev. RGB dioda prikazuje stanje povezave Wi-Fi: oranžna med zagonom, modra med čakanjem na odjemalca, zelena, ko je povezava z računalnikom vzpostavljena in rdeča ob napaki. Dve diodi (pan in zaklep osi) pa prižge program na računalniku. Med gesto za kalibracijo RGB dioda sveti vijolično, po uspešni ponovni kalibraciji pa utripa zeleno.

---

## 5. Povezave in posnetki:

- [Github repozitorij](https://github.com/mairup/esp32-s3_airmouse)
- Posnetek delovanja
