const { section_1, section_2 } = require("./TestFixtures");

describe("CellColors", function(){
    var cc, section, section2;

    beforeEach(function(){
        cc = new CellColors();
        section = section_1();
        section.emailcode = "S1111s1";
        section2 = section_2();
        section2.emailcode = "A2222s1";
    });

    describe("color", function(){
        it("should return a valid rgb color", function(){
            var color = cc.color(section);
            expect(Object.keys(color).sort()).toEqual(["b", "g", "r"]);
            for (var channel in color){
                expect(Number.isInteger(color[channel])).toBe(true);
                expect(color[channel]).toBeGreaterThanOrEqual(0);
                expect(color[channel]).toBeLessThanOrEqual(255);
            };
        });

        it("should return different colors for different classes", function(){
            var color1 = cc.color(section);
            var color2 = cc.color(section2);
            expect(color1).not.toEqual(color2);
        });
    });

    describe("hexToRGB", function(){
        it("returns the correct color", function(){
            expect(cc.hexToRGB("#55ff33")).toEqual({r: 85, g: 255, b: 51});
        });
    });

    describe("textColor", function(){
        it("returns white text on dark backgrounds and black text on light ones", function(){
            expect(cc.textColor({r: 0, g: 0, b: 0})).toEqual("white");
            expect(cc.textColor({r: 255, g: 255, b: 255})).toEqual("black");
        });
    });

});
