import numpy as np
import matplotlib.pyplot as plt

#sample function
def f(x):
  return 3*x**2 - 4*x + 5

#sample graph
xs = np.arange(-5, 5, 0.25) #start, stop, step
ys = f(xs)
plt.plot(xs, ys)

#display graph
#plt.show()

h = 0.000001
x = 2

#derivative tells us the slope of the tangent line to the curve at a specific point. It is calculated as the limit of the difference quotient as h approaches 0. In this case, we are calculating the derivative of f at x = 2 using a small value of h to approximate the limit.
#As below, it can also be obtained by nudging x by a small amount h and calculating the difference in the function values, then dividing by h. This gives us an approximation of the derivative at that point.
print((f(x + h) - f(x))/h) #derivative at x = 2
# derivative of 3x^2 - 4x + 5 is 6x - 4
print(6*x - 4) #derivative at x = 2
#above both should give the same result, which is 8.0

#more complex function
a = 2.0
b = -3.0
c = 10.0
d = a*b + c
print(d)
h = 0.0001

# inputs
a = 2.0
b = -3.0
c = 10.0

d1 = a*b + c
c += h
d2 = a*b + c

print('d1', d1)
print('d2', d2)
print('slope', (d2 - d1)/h)