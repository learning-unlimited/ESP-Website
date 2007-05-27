var ccErrorNo = 0; var ccErrors = new Array ()
ccErrors [0] = "Unknown card type"; ccErrors [1] = "No card number provided"; ccErrors [2] = "Credit card number is in invalid format"; ccErrors [3] = "Credit card number is invalid"; ccErrors [4] = "Credit card number has an inappropriate number of digits"; function checkCreditCard (cardnumber, cardname) { var cards = new Array(); cards [0] = {name: "Visa", length: "13,16", prefixes: "4", checkdigit: true}; cards [1] = {name: "MasterCard", length: "16", prefixes: "51,52,53,54,55", checkdigit: true}; cards [2] = {name: "DinersClub", length: "14,16", prefixes: "300,301,302,303,304,305,36,38,55", checkdigit: true}; cards [3] = {name: "CarteBlanche", length: "14", prefixes: "300,301,302,303,304,305,36,38", checkdigit: true}; cards [4] = {name: "AmEx", length: "15", prefixes: "34,37", checkdigit: true}; cards [5] = {name: "Discover", length: "16", prefixes: "6011,650", checkdigit: true}; cards [6] = {name: "JCB", length: "15,16", prefixes: "3,1800,2131", checkdigit: true}; cards [7] = {name: "enRoute", length: "15", prefixes: "2014,2149", checkdigit: true}; cards [8] = {name: "Solo", length: "16,18,19", prefixes: "6334, 6767", checkdigit: true}; cards [9] = {name: "Switch", length: "16,18,19", prefixes: "4903,4905,4911,4936,564182,633110,6333,6759", checkdigit: true}; cards [10] = {name: "Maestro", length: "16", prefixes: "5020,6", checkdigit: true}; cards [11] = {name: "VisaElectron", length: "16", prefixes: "417500,4917,4913", checkdigit: true}; var cardType = -1; for (var i=0; i<cards.length; i++) { if (cardname.toLowerCase () == cards[i].name.toLowerCase()) { cardType = i; break;}
}
if (cardType == -1) { ccErrorNo = 0; return false;}
if (cardnumber.length == 0) { ccErrorNo = 1; return false;}
cardnumber = cardnumber.replace (/\s/g, ""); var cardNo = cardnumber
var cardexp = /^[0-9]{13,19}$/; if (!cardexp.exec(cardNo)) { ccErrorNo = 2; return false;}
if (cards[cardType].checkdigit) { var checksum = 0; var mychar = ""; var j = 1; var calc; for (i = cardNo.length - 1; i >= 0; i--) { calc = Number(cardNo.charAt(i)) * j; if (calc > 9) { checksum = checksum + 1; calc = calc - 10;}
checksum = checksum + calc; if (j ==1) {j = 2} else {j = 1};}
if (checksum % 10 != 0) { ccErrorNo = 3; return false;}
}
var LengthValid = false; var PrefixValid = false; var undefined; var prefix = new Array (); var lengths = new Array (); prefix = cards[cardType].prefixes.split(","); for (i=0; i<prefix.length; i++) { var exp = new RegExp ("^" + prefix[i]); if (exp.test (cardNo)) PrefixValid = true;}
if (!PrefixValid) { ccErrorNo = 3; return false;}
lengths = cards[cardType].length.split(","); for (j=0; j<lengths.length; j++) { if (cardNo.length == lengths[j]) LengthValid = true;}
if (!LengthValid) { ccErrorNo = 4; return false;}; return true;}
