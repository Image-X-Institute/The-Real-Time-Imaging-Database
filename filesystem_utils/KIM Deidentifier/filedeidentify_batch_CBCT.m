function Deidentifierfile(Copy_dir, value, valuename)

%variables
global KIM

%Input
Firstname = 'Robinson'
Lastname = 'Raymond'
%originalPlanPath = strcat ('C:\Users\csen4522\OneDrive - The University of Sydney (Staff)\Desktop\New folder (3)\Robinson,Raymond_1723198\');
%originalPlanPath = KIM.originalPlanPath
%Copy_dir = strcat ('C:\Users\csen4522\OneDrive - The University of Sydney (Staff)\Desktop\New folder (3)\Master - Copy (4)');
%Copy_dir = KIM.Copy_dir
% Needs to be changed
new = value;
%old='Robinson,Raymond'
%new = 'PAT1'
cd(Copy_dir)

%Looks for no. of CBCTs
list_fx = ls (['*CBCT*']);
no_of_fracs=size(list_fx,1)


for fracno = 1:no_of_fracs
cd(Copy_dir)
%fracdir = strcat(Copy_dir, '\Fx' , num2str(fracno),'\')    
fracdir = strcat(Copy_dir,'\',list_fx(fracno,:),'\')
cd(fracdir) 

%Looks for kV folder
list = ls (['*KV*']);

kVFolder = strcat(fracdir,list,'\')
cd(kVFolder)


% Valid for all files 
%old = strcat(Firstname, ',', Lastname);
% Needs to be changed
old = valuename;

%old='Robinson,Raymond'
% Output
%mkdir (Copy_dir,'KIM-KV\') 
%tic
%copyfile (originalPlanPath , Copy_dir)
%toc

%% Reading trajectory files with Gantry angles
%kVFolder = strcat(Copy_dir,'\KIM-KV\')

%cd(kVFolder)
list = ls([kVFolder '\MarkerLocationsGA*.txt']);
noOfOLTrajFiles = size(list,1);
if(noOfOLTrajFiles>0)
for n = 1:noOfOLTrajFiles
        
        fid=fopen([kVFolder '\MarkerLocationsGA_CouchShift_' num2str(n-1) '.txt']); 
        f=fread(fid,'*char')';
        fclose(fid);
        
        f = regexprep(f,old,new);
        
        fid  = fopen([kVFolder '\MarkerLocationsGA_CouchShift_' num2str(n-1) '.txt'],'w');
        fprintf(fid,'%s',f);
        fclose(fid);
end
end
%% Reading trajectory files without Gantry angles
list = ls([kVFolder '\MarkerLocations_*.txt']);
noOfOLTrajFiles = size(list,1);
if(noOfOLTrajFiles>0)
for n = 1:noOfOLTrajFiles
        fid=fopen([kVFolder '\MarkerLocations_CouchShift_' num2str(n-1) '.txt']); 
        f=fread(fid,'*char')';
        fclose(fid);
        
        f = regexprep(f,old,new);
        
        fid  = fopen([kVFolder '\MarkerLocations_CouchShift_' num2str(n-1) '.txt'],'w');
        fprintf(fid,'%s',f);
        fclose(fid);
end
end
% Changing acquisition logs
cd(fracdir)

if exist('acquisition.log')
       

fid=fopen(['acquisition.log']); 
f=fread(fid,'*char')';
fclose(fid);
f = regexprep(f,old,new);
fid  = fopen(['acquisition.log'],'w');
fprintf(fid,'%s',f);
fclose(fid);

end
end
cd(Copy_dir)
for fracno = 1:no_of_fracs
if(contains(list_fx(fracno,:),old))
Key   = 'CBCT';
Index = strfind(list_fx(fracno,:), Key);
totchr = strlength(list_fx(fracno,:)) 
newChr = extractBetween(list_fx(fracno,:),Index-4,totchr)   
newname= strcat(new,'_CBCT_',newChr)
newpath = strcat(Copy_dir,'\',newname)
oldpath = strcat(Copy_dir,'\',list_fx(fracno,:))
%movefile(oldpath, char(newpath))
movefile(list_fx(fracno,:), char(newname))
%list_fx_new(fracno,:)=strrep(list_fx(fracno,:), old, new)
end
end