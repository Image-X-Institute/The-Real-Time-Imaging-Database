function importEntry() 
{

}

function rejectRequest() 
{
    
}

function displayUploadedFiles()
{

}

function hideAllUploadDetails()
{
    var fileDetailRows = document.getElementsByClassName("upload_details");
    //fileDetailRows.style.display = "none";
    var counter;
    for (counter = 0; counter < fileDetailRows.length; counter++) 
    {
        fileDetailRows[counter].style.display = "none";
    }
    
}
