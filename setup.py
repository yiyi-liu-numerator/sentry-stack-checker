from setuptools import setup

setup(name='sentry-stack-checker',
      version='0.7',
      description='Pylint plugin for checking usage of log.exception',
      long_description=open('README.rst').read(),
      url='https://github.com/yiyi-liu-numerator/sentry-stack-checker',
      author='David Szotten',
      author_email='davidszotten@gmail.com',
      license='MIT',
      py_modules=['sentry_stack_checker'],
      install_requires=['pylint>=3.0.0'],
      zip_safe=False)
