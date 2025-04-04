**TEMA:** 16. Depanarea programelor la distanta:

- Server-ul executa programe constand in instructiuni aritmetice cu atribuirea rezultatului intr-o variabila, instructiuni ce pot include referiri la valorile altor variabile, constante numerice, operatori aritmetici si paranteze, fiecare atribuire constituind o instructiune ce poate fi depanata de la distanta;
- Clientii se conecteaza la server si inregistreaza o serie de puncte de oprire intr-un program identificate prin numele programului si linia fiecarui punct de oprire a executiei;
- Server-ul accepta un singur client care poate intrerupe executia unui program la un moment dat;
- Clientii se pot atasa la un program, pot adauga sau elimina puncte de oprire, sau se pot detasa de la depanarea executiei unui program;
- Aplicatia server lanseaza in executie mai multe programe in paralel;
- Pe durata executiei unui program, clientul care-i depaneaza executia nu mai poate adauga sau elimina puncte de oprire;
- In momentul in care server-ul ajunge in timpul executiei unui program la un punct interceptat de un client, acesta va astepta din partea clientului comenzi pentru evaluarea unei variabile dupa nume sau de setare a valorii acesteia, respectiv va continua pana la urmatorul punct de intrerupere a executiei dupa primirea din partea clientului a unei comenzi in acest sens;
- La incheierea executiei programului depanat, server-ul va notifica clientul care-l monitorizeaza in acest sens.