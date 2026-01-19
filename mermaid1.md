---

title: Animal example

---

classDiagram

&nbsp;   note "From Duck till Zebra"

&nbsp;   Animal <|-- Duck

&nbsp;   note for Duck "can fly<br>can swim<br>can dive<br>can help in debugging"

&nbsp;   Animal <|-- Fish

&nbsp;   Animal <|-- Zebra

&nbsp;   Animal : +int age

&nbsp;   Animal : +String gender

&nbsp;   Animal: +isMammal()

&nbsp;   Animal: +mate()

&nbsp;   class Duck{

&nbsp;       +String beakColor

&nbsp;       +swim()

&nbsp;       +quack()

&nbsp;   }

&nbsp;   class Fish{

&nbsp;       -int sizeInFeet

&nbsp;       -canEat()

&nbsp;   }

&nbsp;   class Zebra{

&nbsp;       +bool is\_wild

&nbsp;       +run()

&nbsp;   }



