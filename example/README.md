# Usage of the example package
A simple example of testing data is provided in the `example` folder. The example package contains a simple example of a package that can be used to test the functionality of the database. 

## Create Trial Structure in the system
In the `LEARN_test` folder, a structure file is provided that can be used to create a trial structure in the system. The trial structure is a hierarchy of the trial that is used to organize the data in the system. To create a trial structure in the system, simply open the web application with the endpoint `/dashboard/trial/management` and upload the trial structure file. 

## Create center in the system
The endpoint for creating center is `/dashboard/centre/management`. In this page, we could check if the centre is already in the database by looking for the centre list. If the new centre is not in the centre list, then just fill the form under ‘Add New Centre’ section and click Submit button. The center required for the example package is `CMN`.

## Import paitent data into the database
The endpoint for importing paitent is `/dashboard/patitents/addnew`. A sample paitent data file is provided in the `LEARN_test` folder. To import the paitent data into the database, simply upload the file to the `bulk import paitent information` section and click the submit button.

## Import sample data into the database
The endpoint for importing sample is `/dashboard/patitents/fractions`. A sample sample data file is provided in the `LEARN_test` folder. To import the sample data into the database, simply upload the file to the `bulk import fraction information` section and click the submit button.