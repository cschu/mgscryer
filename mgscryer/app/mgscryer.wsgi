#!/usr/bin/env python

#/congo/DB/MGSCRYER/mgscryer_env/bin/python3

import sys
import os

#sys.path.insert(0, "/congo/DB/MGSCRYER/mgscryer_env/lib/python3.6/site-packages")
#sys.path.insert(0, "/congo/DB/MGSCRYER/mgscryer_py27_env/lib/python2.7/site-packages")
#sys.path.insert(0, "/congo/DB/MGSCRYER/mgscryer_env/lib/python2.7/site-packages")
#sys.stderr.write(sys.version)
sys.path.insert(0, "/congo/DB/MGSCRYER/mgscryer.embl.de")


#from flask import Flask

#app = Flask(__name__)

#@app.route("/")
#def hiya():
#    return "BLARGH"


#if __name__ == "__main__":
#    app.run()

from mgscryer import app as application


"""
#print(sys.version, file=stderr)
#path = os.path.dirname(os.path.abspath(__file__))
#sys.path.insert(0, os.path.join(path, "env", "lib", "python2.7", "site-packages"))
#sys.path.insert(1, os.path.join(path, "env", "lib64", "python2.7", "site-packages"))


import cherrypy
import pkg_resources

#from marine_report import wsgi
#from marine_report.db import ReportDB
#from marine_report.handler import SplashHandler

def application(environ, start_response):
    app_folder = pkg_resources.resource_filename(__name__, "/")
    #app_folder = os.path.abspath(os.path.join(path, "env", "lib", "python2.7", "site-packages", "marine_report"))
    cherrypy.tree.mount(
        None,
        "",
        {
            "/": {
                "tools.gzip.on": True,
                "tools.staticdir.on": True,
                "tools.staticdir.index": "index.html",
                "tools.staticdir.dir": os.path.join(path, "public"),
            },
            #"/js": {
            #    "tools.staticdir.on": True,
            #    "tools.staticdir.dir": os.path.join(app_folder, "js")
            #},
            #"/js/vendor": {
            #    "tools.gzip.mime_types": ['application/javascript', 'text/css'],
            #    "tools.staticdir.on": True,
            #    "tools.staticdir.dir": os.path.join(app_folder, "vendor")
            #},
            #"/static/fonts": {
            #    'tools.gzip.on': False,
            #    "tools.staticdir.on": True,
            #    "tools.staticdir.dir": os.path.join(app_folder, "vendor", "fonts")
            #},
            #"/static/img": {
            #    'tools.gzip.on': False,
            #    "tools.staticdir.on": True,
            #    "tools.staticdir.dir": os.path.join(app_folder, "img")
            #},
            #"/graphs": {
            #    'tools.gzip.on': False,
            #    "tools.staticdir.on": True,
            #    "tools.staticdir.dir": os.path.join(app_folder, "graphs")
            #},
        }
    )

    #cherrypy.tree.mount(
    #    SplashHandler(db=ReportDB(os.path.join(path, "marine.db3"))), 
    #    "/datasets/marine", 
    #    {"": {"tools.gzip.on": True}},
    #)

    #cherrypy.tree.mount(
    #    SplashHandler(db=ReportDB(os.path.join(path, "crc.db3"))),
    #    "/datasets/crc",
    #    {"": {"tools.gzip.on": True}},
    #)

    #cherrypy.tree.mount(
    #    SplashHandler(db=ReportDB(os.path.join(path, "9genomes.db3"))),
    #    "/datasets/9genomes",
    #    {"": {"tools.gzip.on": True}},
    #)

    #cherrypy.config.update({
    #    'environment': 'production',
    #    'log.error_file': os.path.join(path, 'gecco.log'), 
    #})
    
    return cherrypy.tree(environ, start_response)
"""
