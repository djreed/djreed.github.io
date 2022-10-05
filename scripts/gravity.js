// JS Physics Engine provided by MatterJS: https://brm.io/matter-js/
// Source code ends up being ~77 kilobytes, which is smaller than other engines
// that I've found so far
// (https://github.com/liabru/matter-js/blob/master/build/matter.min.js)

const fillColor = 'white';
const strokeColor = '#373737';
const backgroundColor = '#efefef';

// auxiliary functions
var aux = {};

// Math conversion
aux.degreesToRadians = function (degrees) {
  return degrees * Math.PI / 180; 
};

// Rather than use JQuery for element parameters
// Source: https://youmightnotneedjquery.com/
aux.offset = function (el) {
  box = el.getBoundingClientRect();
  docElem = document.documentElement;
  return {
    top: box.top + window.pageYOffset - docElem.clientTop,
    left: box.left + window.pageXOffset - docElem.clientLeft
  };
}

// Constants for mobile-friendly decision-making
const IS_MOBILE = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
const IS_APPLE  = /iPhone|iPad|iPod/i.test(navigator.userAgent);
const MOBILE_OR_APPLE = IS_MOBILE || IS_APPLE

console.log('Mobile?', IS_MOBILE)
console.log('Apple?', IS_APPLE)

function prepareCanvas(options) {
  
  if (!options.canvasWidth) {
    throw new Error('canvasWidth is required');
  }
  
  if (!options.canvasHeight) {
    throw new Error('canvasHeight is required');
  }
  
  if (!options.canvas) {
    throw new Error('canvas is required');
  }
  
  // wall constiables
  var wallWidth = 50;
  
  var canvasWidth = options.canvasWidth;
  var canvasHeight = options.canvasHeight;
  var canvas = options.canvas;
  
  // direct access to classes
  var Engine = Matter.Engine;
  var Render = Matter.Render;
  var Common = Matter.Common;
  var Bodies = Matter.Bodies;
  var Runner = Matter.Runner;
  var Composites = Matter.Composites;
  var Events = Matter.Events;
  var World = Matter.World;
  var Vector = Matter.Vector;
  var Mouse = Matter.Mouse;
  var MouseConstraint = Matter.MouseConstraint;
  
  // instances
  var engine = Engine.create();
  var world  = engine.world;
  
  // define world-wide configs
  world.gravity = {
    x: Common.random(-0.2, 0.2),
    // y: 1.4,
    y: Common.random(0.2, 2),
  };
  
  var pixelRatio = 1
  
  var render = Render.create({
    canvas: canvas,
    engine: engine,
    options: {
      pixelRatio: pixelRatio,
      width: canvasWidth,
      height: canvasHeight,
      wireframes: false,
      background: backgroundColor,
    }
  });
  
  Render.run(render);
  
  // create runner
  var runner = Runner.create();
  Runner.run(runner, engine);
  
  // create squares
  var squaresStackCompositeTop = MOBILE_OR_APPLE ? 50 : -500;
  var squaresStackComposite = Composites.stack(0, squaresStackCompositeTop, 32, 5, 0, 0,
    function (x, y) {
      var size = Common.random(5, 60);
      var angle = aux.degreesToRadians(Common.random(0, 45));
      
      return Bodies.rectangle(
        x,
        y,
        size,
        size,
        {
          angle: angle,
          restitution: 0.1,
          render: {
            fillStyle: fillColor,
            strokeStyle: strokeColor,
            lineWidth: 2,
          }
        }
      );
    }
  );
  // make a clone of the squares bodies
  var squares = squaresStackComposite.bodies.concat([]);
  
  // add bodies to the world
  World.add(world, [
    squaresStackComposite,
    // roof
    Bodies.rectangle(
      canvasWidth / 2,
      -1.5 * canvasHeight,
      canvasWidth,
      wallWidth,
      {
        isStatic: true,
        render: {
          visible: false,
        }
      }
    ),
    // floor
    Bodies.rectangle(
      canvasWidth / 2,
      canvasHeight + (wallWidth / 2),
      canvasWidth,
      wallWidth,
      {
        isStatic: true,
        render: {
          visible: false,
        }
      }
    ),
    // right
    Bodies.rectangle(
      canvasWidth + wallWidth / 2,
      canvasHeight / 2,
      wallWidth,
      canvasHeight * 100,
      {
        isStatic: true,
        render: {
          visible: false,
        }
      }
    ),
    // left
    Bodies.rectangle(
      - wallWidth / 2,
      canvasHeight / 2,
      wallWidth,
      canvasHeight * 100,
      {
        isStatic: true,
        render: {
          visible: false,
        }
      }
    ),
  ]);
  
  // On non-mobile windows we want the JSON card to be an obstacle for squares
  if (!MOBILE_OR_APPLE) {
    setTimeout(function () {
      // add obstacle for Card
      var card = document.querySelector('.card');
      var cardWidth = card.getBoundingClientRect().width;
      var cardHeight = card.getBoundingClientRect().height;
      var cardPos = aux.offset(card);
      
      // obstacle
      World.add(world, Bodies.rectangle(
        cardPos.left + (cardWidth/2),
        cardPos.top + (cardHeight/2),
        cardWidth,
        cardHeight,
        {
          isStatic: true,
          render: {
            fillStyle: 'transparent',
            strokeStyle: 'transparent',
            lineWidth: 0,
          }
        }
      ));
    }, 300);
  }
  
  // On mobile windows screen space is too important, so don't collide w/ card
  if (MOBILE_OR_APPLE) {
    // no mouse control in mobile
    if (window.DeviceMotionEvent !== undefined) {
      // mobile roof
      World.add(world, [
        Bodies.rectangle(
          canvasWidth / 2,
          (-1 * (wallWidth / 2)),
          canvasWidth,
          wallWidth,
          {
            isStatic: true,
            render: {
              visible: false,
            }
          }
        ),
      ]);
      
      window.addEventListener('devicemotion', function(e) {
        console.log('devicemotion', e)
        
        var ax = e.accelerationIncludingGravity.x * 0.6;
        var ay = e.accelerationIncludingGravity.y * 0.6;
        
        // define world-wide configs
        world.gravity = {
          x: ax,      // west to east axis
          y: ay * -1, // south to north axis, so inverse is "ground-facing"
        };
      });
    }

  } else {
    // add mouse control
    var mouse = Mouse.create(render.canvas);
    var mouseConstraint = MouseConstraint.create(engine, {
      mouse: mouse,
      constraint: {
        stiffness: 1,
        render: {
          visible: false,
        }
      }
    });

    // https://github.com/liabru/matter-js/issues/84
    // mouse.element.removeEventListener("mousewheel", mouse.mousewheel);
    // mouse.element.removeEventListener("DOMMouseScroll", mouse.mousewheel);
    
    World.add(world, mouseConstraint);
    
    // mouse events
    var isDragging = false;
    var wasDragging = false;
    Events.on(mouseConstraint, 'startdrag', function (e) {
      isDragging = true;
    });
    Events.on(mouseConstraint, 'enddrag', function (e) {
      isDragging = false;
      wasDragging = true;
      
      setTimeout(function () {
        wasDragging = false;
      }, 500);
    });
    Events.on(mouseConstraint, 'mousemove', function (e) {
      
      if (isDragging) {
        return;
      }
      
      // console.log('mousemove', e.mouse.absolute);
      var mousePosition = e.mouse.absolute;
      var target = Matter.Query.point(squares, mousePosition)[0];
      
      if (!target) {
        return;
      }
      
      var magnitude = 0.05 * target.mass;
      var direction = Matter.Vector.create(0, -1); // always up
      var force = Matter.Vector.mult(direction, magnitude);
      Matter.Body.applyForce(target, target.position, force);
    });
    
    Events.on(mouseConstraint, 'mouseup', function (e) {
      
      if (wasDragging) {
        return;
      }
      
      // console.log('mouseup', e);
      var size = Common.random(5, 60);
      var angle = aux.degreesToRadians(Common.random(0, 45));
      
      var newSquare = Bodies.rectangle(
        e.mouse.mouseupPosition.x,
        e.mouse.mouseupPosition.y,
        size,
        size,
        {
          angle: angle,
          restitution: 0.1,
          render: {
            fillStyle: fillColor,
            strokeStyle: strokeColor,
            lineWidth: 2,
          }
        }
      );
      
      // save to the list of squares
      squares.push(newSquare);
      World.add(world, newSquare);
    });
  }
  
  return {
    engine: engine,
    runner: runner,
    render: render,
    canvas: render.canvas,
    stop: function() {
      Matter.Render.stop(render);
      Matter.Runner.stop(runner);
    }
  }
}

// Document height/width in a generalized way, so far from testing this has
// worked on Mobile windows without error
// https://stackoverflow.com/questions/1145850/how-to-get-height-of-entire-document-with-javascript
var win = window,
    doc = document,
    docElem = doc.documentElement,
    body = doc.getElementsByTagName('body')[0],
    width = win.innerWidth || docElem.clientWidth || body.clientWidth,
    height = win.innerHeight|| docElem.clientHeight|| body.clientHeight;
console.log(width + ' × ' + height);

var matterCtrl = prepareCanvas({
  canvas: document.querySelector('#gravity-canvas'),
  canvasWidth: width,
  canvasHeight: height,
});
