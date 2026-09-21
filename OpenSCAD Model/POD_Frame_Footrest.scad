include <../../OpenSCAD_Lib/MakeInclude.scad>
include <../../OpenSCAD_Lib/chamferedCylinders.scad>

firstLayerHeight = 0.2;
layerHeight = 0.2;

polygonMinX = 20.25 + 0.27;
polygonMinY = 7.5; //10.06628768;

polygonMaxY = 63.14799479;

polygonOffset = [0, polygonMinY];
gridSize_mm = 5;

footrestPoints = 
[
    gridSize_mm*([-polygonMinX, polygonMinY]-polygonOffset),
    gridSize_mm*([-17.75, 31.03502665]-polygonOffset), 
    gridSize_mm*([-17.50, 33.19967738]-polygonOffset), 
    gridSize_mm*([-17.25, 35.3602578]-polygonOffset), 
    gridSize_mm*([-17.00, 37.5086703]-polygonOffset), 
    gridSize_mm*([-16.75, 39.62907459]-polygonOffset), 
    gridSize_mm*([-16.50, 41.7007557]-polygonOffset), 
    gridSize_mm*([-16.25, 43.70019354]-polygonOffset), 
    gridSize_mm*([-16.00, 45.60026979]-polygonOffset), 
    gridSize_mm*([-15.75, 47.37051208]-polygonOffset), 
    gridSize_mm*([-15.50, 48.98133918]-polygonOffset), 
    gridSize_mm*([-15.25, 50.40953329]-polygonOffset), 
    gridSize_mm*([-15.00, 51.64535016]-polygonOffset), 
    gridSize_mm*([-14.75, 52.6975567]-polygonOffset), 
    gridSize_mm*([-14.50, 53.58913917]-polygonOffset), 
    gridSize_mm*([-14.25, 54.34502617]-polygonOffset), 
    gridSize_mm*([-14.00, 54.98950369]-polygonOffset), 
    gridSize_mm*([-13.75, 55.54230546]-polygonOffset), 
    gridSize_mm*([-13.50, 56.02005526]-polygonOffset), 
    gridSize_mm*([-13.25, 56.4335427]-polygonOffset), 
    gridSize_mm*([-13.00, 56.79193399]-polygonOffset), 
    gridSize_mm*([-12.75, 57.10439526]-polygonOffset), 
    gridSize_mm*([-12.50, 57.38009266]-polygonOffset), 
    gridSize_mm*([-12.25, 57.62819232]-polygonOffset), 
    gridSize_mm*([-12.00, 57.85786038]-polygonOffset), 
    gridSize_mm*([-11.75, 58.07737273]-polygonOffset), 
    gridSize_mm*([-11.50, 58.29140427]-polygonOffset), 
    gridSize_mm*([-11.25, 58.50238716]-polygonOffset), 
    gridSize_mm*([-11.00, 58.71110389]-polygonOffset), 
    gridSize_mm*([-10.75, 58.91798402]-polygonOffset), 
    gridSize_mm*([-10.50, 59.12244986]-polygonOffset), 
    gridSize_mm*([-10.25, 59.32372687]-polygonOffset), 
    gridSize_mm*([-10.00, 59.52108014]-polygonOffset), 
    gridSize_mm*([-9.75, 59.71377562]-polygonOffset), 
    gridSize_mm*([-9.50, 59.90107925]-polygonOffset), 
    gridSize_mm*([-9.25, 60.08225698]-polygonOffset), 
    gridSize_mm*([-9.00, 60.25657475]-polygonOffset), 
    gridSize_mm*([-8.75, 60.42351575]-polygonOffset), 
    gridSize_mm*([-8.50, 60.58343218]-polygonOffset), 
    gridSize_mm*([-8.25, 60.73689353]-polygonOffset), 
    gridSize_mm*([-8.00, 60.88446923]-polygonOffset), 
    gridSize_mm*([-7.75, 61.02661302]-polygonOffset), 
    gridSize_mm*([-7.50, 61.16340564]-polygonOffset), 
    gridSize_mm*([-7.25, 61.29496747]-polygonOffset), 
    gridSize_mm*([-7.00, 61.42143341]-polygonOffset), 
    gridSize_mm*([-6.75, 61.54292945]-polygonOffset), 
    gridSize_mm*([-6.50, 61.65954578]-polygonOffset), 
    gridSize_mm*([-6.25, 61.77136368]-polygonOffset), 
    gridSize_mm*([-6.00, 61.87846441]-polygonOffset), 
    gridSize_mm*([-5.75, 61.9809124]-polygonOffset), 
    gridSize_mm*([-5.50, 62.07872302]-polygonOffset), 
    gridSize_mm*([-5.25, 62.17199243]-polygonOffset), 
    gridSize_mm*([-5.00, 62.26084926]-polygonOffset), 
    gridSize_mm*([-4.75, 62.34540173]-polygonOffset), 
    gridSize_mm*([-4.50, 62.42567627]-polygonOffset), 
    gridSize_mm*([-4.25, 62.50167892]-polygonOffset), 
    gridSize_mm*([-4.00, 62.57341567]-polygonOffset), 
    gridSize_mm*([-3.75, 62.64089253]-polygonOffset), 
    gridSize_mm*([-3.50, 62.70411551]-polygonOffset), 
    gridSize_mm*([-3.25, 62.76309063]-polygonOffset), 
    gridSize_mm*([-3.00, 62.81782388]-polygonOffset), 
    gridSize_mm*([-2.75, 62.86832129]-polygonOffset), 
    gridSize_mm*([-2.50, 62.91458886]-polygonOffset), 
    gridSize_mm*([-2.25, 62.9566326]-polygonOffset), 
    gridSize_mm*([-2.00, 62.99445852]-polygonOffset), 
    gridSize_mm*([-1.75, 63.02807263]-polygonOffset), 
    gridSize_mm*([-1.50, 63.05748093]-polygonOffset), 
    gridSize_mm*([-1.25, 63.08268945]-polygonOffset), 
    gridSize_mm*([-1.00, 63.10370418]-polygonOffset), 
    gridSize_mm*([-0.75, 63.12056316]-polygonOffset), 
    gridSize_mm*([-0.50, 63.1334325]-polygonOffset), 
    gridSize_mm*([-0.25, 63.14251033]-polygonOffset), 
    gridSize_mm*([0.00, 63.14799479]-polygonOffset), 
    gridSize_mm*([0.25, 63.14251033]-polygonOffset), 
    gridSize_mm*([0.50, 63.1334325]-polygonOffset), 
    gridSize_mm*([0.75, 63.12056316]-polygonOffset), 
    gridSize_mm*([1.00, 63.10370418]-polygonOffset), 
    gridSize_mm*([1.25, 63.08268945]-polygonOffset), 
    gridSize_mm*([1.50, 63.05748093]-polygonOffset), 
    gridSize_mm*([1.75, 63.02807263]-polygonOffset), 
    gridSize_mm*([2.00, 62.99445852]-polygonOffset), 
    gridSize_mm*([2.25, 62.9566326]-polygonOffset), 
    gridSize_mm*([2.50, 62.91458886]-polygonOffset), 
    gridSize_mm*([2.75, 62.86832129]-polygonOffset), 
    gridSize_mm*([3.00, 62.81782388]-polygonOffset), 
    gridSize_mm*([3.25, 62.76309063]-polygonOffset), 
    gridSize_mm*([3.50, 62.70411551]-polygonOffset), 
    gridSize_mm*([3.75, 62.64089253]-polygonOffset), 
    gridSize_mm*([4.00, 62.57341567]-polygonOffset), 
    gridSize_mm*([4.25, 62.50167892]-polygonOffset), 
    gridSize_mm*([4.50, 62.42567627]-polygonOffset), 
    gridSize_mm*([4.75, 62.34540173]-polygonOffset), 
    gridSize_mm*([5.00, 62.26084926]-polygonOffset), 
    gridSize_mm*([5.25, 62.17199243]-polygonOffset), 
    gridSize_mm*([5.50, 62.07872302]-polygonOffset), 
    gridSize_mm*([5.75, 61.9809124]-polygonOffset), 
    gridSize_mm*([6.00, 61.87846441]-polygonOffset), 
    gridSize_mm*([6.25, 61.77136368]-polygonOffset), 
    gridSize_mm*([6.50, 61.65954578]-polygonOffset), 
    gridSize_mm*([6.75, 61.54292945]-polygonOffset), 
    gridSize_mm*([7.00, 61.42143341]-polygonOffset), 
    gridSize_mm*([7.25, 61.29496747]-polygonOffset), 
    gridSize_mm*([7.50, 61.16340564]-polygonOffset), 
    gridSize_mm*([7.75, 61.02661302]-polygonOffset), 
    gridSize_mm*([8.00, 60.88446923]-polygonOffset), 
    gridSize_mm*([8.25, 60.73689353]-polygonOffset), 
    gridSize_mm*([8.50, 60.58343218]-polygonOffset), 
    gridSize_mm*([8.75, 60.42351575]-polygonOffset), 
    gridSize_mm*([9.00, 60.25657475]-polygonOffset), 
    gridSize_mm*([9.25, 60.08225698]-polygonOffset), 
    gridSize_mm*([9.50, 59.90107925]-polygonOffset), 
    gridSize_mm*([9.75, 59.71377562]-polygonOffset), 
    gridSize_mm*([10.00, 59.52108014]-polygonOffset), 
    gridSize_mm*([10.25, 59.32372687]-polygonOffset), 
    gridSize_mm*([10.50, 59.12244986]-polygonOffset), 
    gridSize_mm*([10.75, 58.91798402]-polygonOffset), 
    gridSize_mm*([11.00, 58.71110389]-polygonOffset), 
    gridSize_mm*([11.25, 58.50238716]-polygonOffset), 
    gridSize_mm*([11.50, 58.29140427]-polygonOffset), 
    gridSize_mm*([11.75, 58.07737273]-polygonOffset), 
    gridSize_mm*([12.00, 57.85786038]-polygonOffset), 
    gridSize_mm*([12.25, 57.62819232]-polygonOffset), 
    gridSize_mm*([12.50, 57.38009266]-polygonOffset), 
    gridSize_mm*([12.75, 57.10439526]-polygonOffset), 
    gridSize_mm*([13.00, 56.79193399]-polygonOffset), 
    gridSize_mm*([13.25, 56.4335427]-polygonOffset), 
    gridSize_mm*([13.50, 56.02005526]-polygonOffset), 
    gridSize_mm*([13.75, 55.54230546]-polygonOffset), 
    gridSize_mm*([14.00, 54.98950369]-polygonOffset), 
    gridSize_mm*([14.25, 54.34502617]-polygonOffset), 
    gridSize_mm*([14.50, 53.58913917]-polygonOffset), 
    gridSize_mm*([14.75, 52.6975567]-polygonOffset), 
    gridSize_mm*([15.00, 51.64535016]-polygonOffset), 
    gridSize_mm*([15.25, 50.40953329]-polygonOffset), 
    gridSize_mm*([15.50, 48.98133918]-polygonOffset), 
    gridSize_mm*([15.75, 47.37051208]-polygonOffset), 
    gridSize_mm*([16.00, 45.60026979]-polygonOffset), 
    gridSize_mm*([16.25, 43.70019354]-polygonOffset), 
    gridSize_mm*([16.50, 41.7007557]-polygonOffset), 
    gridSize_mm*([16.75, 39.62907459]-polygonOffset), 
    gridSize_mm*([17.00, 37.5086703]-polygonOffset), 
    gridSize_mm*([17.25, 35.3602578]-polygonOffset), 
    gridSize_mm*([17.50, 33.19967738]-polygonOffset), 
    gridSize_mm*([17.75, 31.03502665]-polygonOffset), 
    gridSize_mm*([polygonMinX, polygonMinY]-polygonOffset)
];

footrestPointsMinY = min([ for (p = footrestPoints) p[1] ]);
echo(str("footrestPoints min` Y = ", footrestPointsMinY));

footrestPointsMaxY = max([ for (p = footrestPoints) p[1] ]);
echo(str("footrestPoints max Y = ", footrestPointsMaxY));

echo(str("Base X = ", 2*footrestPoints[0][0]));

n = len(footrestPoints);

echo(str("len(footrestPoints) = ", n));

footrestIndicies = [[ for (i = [0 : 1 : n-1]) i ]];

echo(str("len(footrestIndicies[0]) = ", len(footrestIndicies[0])));

makeRendering = false;
makeDxfCore = false;
makeDxfPlate = false;

module core(h)
{
    difference() 
    {
        linear_extrude(height=h) polygon(footrestPoints, footrestIndicies);

        topCutout();
        bottomCutout();
    }
}

module plate(h)
{
    difference()
    {
        minkowski() 
        {
            linear_extrude(height=h-1) polygon(footrestPoints, footrestIndicies);
            cylinder(d=25, h=1);
        }
        tcu([-200, -400+nothing, -200], 400);

        topCutout();
        bottomCutout();
    }
}

topCutoutWidth = 40;
topCutoutY = 89;

module topCutout()
{

}

bottomCutoutWidth = 44;
bottomCutoutY = 80;
module bottomCutout()
{

}

module itemModule()
{
    compositeZ = 3;
    coreZ = 12; //0.5*mm; 
    aluminumZ = 3; //0.125*mm

    // Composite face:
	translate([0,0,-compositeZ]) color("black") core(h=compositeZ);

    // Plywood core:
	color("tan") core(h=coreZ);

    // Aluminum plate:
	translate([0,0,coreZ]) color("silver") plate(h=aluminumZ);
}

module clip(d=0)
{
	//tc([-200, -400-d, -10], 400);
}

if(developmentRender)
{
	// display() itemModule();

    display() projection() core(h=2);
    display() translate([-250,0,0]) projection() plate(h=2);
}
else
{
    if(makeRendering) itemModule();
	if(makeDxfCore) projection() core(h=2);
	if(makeDxfPlate) projection() plate(h=2);
}
