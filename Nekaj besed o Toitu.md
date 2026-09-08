# Toit in programiranje mikrokontrolerjev v njegovem okolju

---

## Predgovor

Pri projektu za VIN sem se odločil za uporabo jezika Toit. Želel sem poskusiti kakšno novo tehnologijo, saj so mikrokontrolerji še vedno večinoma pisani v nižjih visokonivojskih jezikih, kot je C.

Toit je name dal zelo privlačen prvi vtis, saj sta ga razvila inženirja iz Googla, ki sta med drugim sodelovala pri Dartu, s katerim imam pa že nekaj izkušenj in je prijeten za uporabo. Pri Toitu sem opazil veliko podobnosti, zato sem ga še toliko bolj želel preizkusiti.

---

## Na kratko o Toitu in orodju Jaguar

Toit je moderen, visokonivojski, objektno usmerjen programski jezik. Pred izvajanjem je preveden v strojno kodo. Podpira samo naprave podjetja Espressif, kar so mikrokontrolerji v družini esp32. Naš projekt je uporabljal esp32-S3 SoC.

Na mikrokontrolerju se izvaja Toitov navidezni stroj. Pod pokrovom ta stroj uporablja FreeRTOS, v katerem implementira vse funcijonalnosti jezika, kot je razporejanje niti, upravljanje s pomnilnikom in upravljanje z V/I operacijami.  
Pri tem bi samo dodal, da razporejanje niti deluje na osnovi sodelovalnega krožnega razvrščevalnika. Osnovna enota za nit (ki jih naš navidezni stroj razvršča) je v Toitu imenovana Task. Njihova stvaritev je podobna objektom, prav tako za njihove vire poskrbi garbage collector.

Kot razvijalec, pa delaš na nivoju vsebnikov. ki so izvajani na navideznem stroju na mikrokontrolerju. Vsak program se na mikrokontroler namesti v svojem zabojniku in ima povsem ločen naslovni prostor. Programi med seboj komunicirajo (samo) preko medprocesnih vmesnikov, ki nam jih ponuja in upravlja Toitov navidezni stroj.

Na projektu smo se, glede na velikost problema, odločili za uporabo samo enega aplikacijskega vsebnika. Tako na mikrokontrolerju tečeta samo 2, naša aplikacija in jaguar.

Kot edini drug program, izvajan na našem mikrokontrolerju v projektu, si Jaguar zasluži nekaj besed zase.

Jaguar je program, ki nam ponuja vmesnik v ukazni vrstici, s katerim lahko upravljamo z vsebniki na našem mikrokontrolerja, kar lahko opravljamo preko Wi-Fi brezžično.

Po mojih izkušnjah traja posodobitev našega programa (sicer z monolitno zasnovo) v povprečju približno 5 sekund, do 10 v težjih razmerah.

---

## Misli po uporabi jezika v projektu

Z veseljem poročam, da je bil toit precej prijeten za uporabo. Kot objektno usmerjen jezik je že v osnovi zelo podoben mnogim drugim popularnim jezikom. Všeč mi je, da lepo doda in tudi v osnovi zelo dobro omogoči bolj deklarativne pristope pisanja kode, ki se odlično skladajo z objektno strukturo jezika.

Rekel bi, da so tudi jezikovni modeli bili bolj uspešni pri pisanju kode, kot bi bili pri nižjenivojskih jezikih. Sicer nimam podatkov za primerjavo dejanskih rezultatov z drugimi jeziki, lahko pa povem, da sem kot programer lažje in hitreje razumel kodo, ki so jo spisali agenti, oni pa so imeli lažje delo zaradi Toitove bližine naravnemu jeziku.

Iteracije med različnimi prototipi funkcionalnosti našega projekta so bile hitre in enostavne. Problemi so nastali, ko smo začeli še sami uporabljati Wi-Fi anteno, vendar je bilo vse hitro rešljivo in bolj napaka programerja.

Glede hitrosti tudi nimam dejanskih meritev. Za našo uporabo je bil dovolj hiter, več pa nisem želel. Sama koda je prevedena v strojno kodo, zato se mi zdi, da ne bi smela biti preveč počasna, kljub abstrakcijam in samodejnem upravljanju s pomilnikom. Nekateri viri poročajo, da je “veliko hitrejši od MicroPython okolja”, vendar sam nimam izkušenj.

---

## Zaključek

Uporaba jezika Toit in njegovega razvojnega okolja se je izkazala za uspešno. Med razvojem projekta sem pogosto opazil, kako nam izbrano okolje zelo pomaga pri danem problemu, ki bi bil v drugem okolju verjetno veliko zahtevnejši. Rezultat pa je (meni) zanimiv projekt, razvit v razmeroma kratkem času z majhnim številom razvijalcev.

*Avtor: Mai Rupnik*